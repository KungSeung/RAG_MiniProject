"""
강남 맛집 RAG 시스템 (벡터 검색 버전)

- 태그 포함된 content를 임베딩
- 벡터 유사도 검색으로 "점심", "혼밥" 등 의미 검색 가능
"""

import json
import os
import math
import random
import requests
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
import anthropic
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# ============================================================
# 1. 설정
# ============================================================

# 환경 변수에서 API 키 로드 (필수)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

# 필수 환경 변수 체크
required_vars = {
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_KEY": SUPABASE_KEY,
    "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
    "KAKAO_API_KEY": KAKAO_API_KEY
}

missing_vars = [name for name, value in required_vars.items() if not value]
if missing_vars:
    print("❌ 오류: 다음 환경 변수가 설정되지 않았습니다:")
    for var in missing_vars:
        print(f"   - {var}")
    print("\n💡 .env 파일을 생성하고 필요한 API 키를 설정하세요.")
    print("   예시: .env.example 파일을 참고하세요.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# 임베딩 모델 (무료)
embedding_model = None

def get_embedding_model():
    global embedding_model
    if embedding_model is None:
        print("🔄 임베딩 모델 로딩 중...")
        embedding_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    return embedding_model

def get_embedding(text: str) -> list:
    model = get_embedding_model()
    return model.encode(text).tolist()


# ============================================================
# 2. Supabase 테이블 (SQL Editor에서 실행)
# ============================================================

SETUP_SQL = """
-- 기존 테이블 삭제
DROP TABLE IF EXISTS places;
DROP FUNCTION IF EXISTS match_places_vector;

-- pgvector 확장
CREATE EXTENSION IF NOT EXISTS vector;

-- 새 테이블 (태그 포함)
CREATE TABLE places (
    id bigserial PRIMARY KEY,
    place_id text UNIQUE NOT NULL,
    name text NOT NULL,
    category text,
    place_type text,
    address text,
    phone text,
    x text,
    y text,
    distance text,
    url text,
    tags text[],           -- 태그 배열
    meal_time text[],      -- 식사 시간
    situation text[],      -- 상황
    vibe text[],           -- 분위기
    content text,          -- 풍부한 설명 (임베딩 대상)
    embedding vector(768),
    created_at timestamptz DEFAULT now()
);

-- 벡터 검색 함수
CREATE OR REPLACE FUNCTION match_places_vector(
    query_embedding vector(768),
    match_count int DEFAULT 20
)
RETURNS TABLE (
    id bigint,
    place_id text,
    name text,
    category text,
    place_type text,
    address text,
    phone text,
    x text,
    y text,
    distance text,
    url text,
    tags text[],
    meal_time text[],
    situation text[],
    vibe text[],
    content text,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        places.id,
        places.place_id,
        places.name,
        places.category,
        places.place_type,
        places.address,
        places.phone,
        places.x,
        places.y,
        places.distance,
        places.url,
        places.tags,
        places.meal_time,
        places.situation,
        places.vibe,
        places.content,
        1 - (places.embedding <=> query_embedding) AS similarity
    FROM places
    ORDER BY places.embedding <=> query_embedding
    LIMIT match_count;
$$;
"""


# ============================================================
# 3. 데이터 저장 (태그 포함)
# ============================================================

def store_places_with_tags(data_file: str = "gangnam_places_with_tags.json"):
    """태그 포함된 데이터를 임베딩하여 Supabase에 저장"""
    
    print(f"📂 {data_file} 로딩...")
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    all_places = []
    
    # 음식점
    for place in data["restaurants"]:
        all_places.append({"place": place, "place_type": "restaurant"})
    
    # 카페
    for place in data["cafes"]:
        all_places.append({"place": place, "place_type": "cafe"})
    
    print(f"📊 총 {len(all_places)}개 장소 임베딩 & 저장 중...")
    
    for i, item in enumerate(all_places):
        place = item["place"]
        
        # content가 없으면 기본값 생성
        content = place.get("content", "")
        if not content:
            content = f"{place['name']}은(는) {place['category']} 전문점입니다."
        
        # 태그들을 content에 추가 (임베딩 품질 향상)
        tags_text = " ".join(place.get("tags", []))
        full_content = f"{content} {tags_text}"
        
        # 임베딩 생성
        embedding = get_embedding(full_content)
        
        # Supabase에 저장
        record = {
            "place_id": place["id"],
            "name": place["name"],
            "category": place["category"],
            "place_type": item["place_type"],
            "address": place["address"],
            "phone": place.get("phone", ""),
            "x": place["x"],
            "y": place["y"],
            "distance": place["distance"],
            "url": place["url"],
            "tags": place.get("tags", []),
            "meal_time": place.get("meal_time", []),
            "situation": place.get("situation", []),
            "vibe": place.get("vibe", []),
            "content": content,
            "embedding": embedding
        }
        
        supabase.table("places").upsert(record, on_conflict="place_id").execute()
        
        if (i + 1) % 50 == 0 or i == len(all_places) - 1:
            print(f"  [{i+1}/{len(all_places)}] 저장 완료")
    
    print("✅ 모든 데이터 저장 완료!")


# ============================================================
# 4. 위치 검색 (카카오 API)
# ============================================================

def get_coordinates(query: str) -> dict:
    """주소/건물명 → 좌표"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": KAKAO_API_KEY}

    response = requests.get(url, headers=headers, params={"query": query, "size": 1})
    
    if response.status_code == 200 and response.json()["documents"]:
        place = response.json()["documents"][0]
        return {
            "name": place["place_name"],
            "x": float(place["x"]),
            "y": float(place["y"])
        }
    return None


def calc_distance(lat1, lon1, lat2, lon2) -> int:
    """두 좌표 사이 거리 (미터)"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    return int(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))


# ============================================================
# 5. 벡터 검색 (핵심!)
# ============================================================

def search_by_vector(query: str, limit: int = 20) -> list:
    """
    벡터 유사도 검색
    
    "점심에 혼밥하기 좋은 곳" → 의미적으로 비슷한 장소 반환
    """
    # 질문을 임베딩
    query_embedding = get_embedding(query)
    
    # Supabase RPC 호출
    result = supabase.rpc(
        "match_places_vector",
        {
            "query_embedding": query_embedding,
            "match_count": limit
        }
    ).execute()
    
    return result.data


# ============================================================
# 6. AI 질문 파싱
# ============================================================

def parse_question(user_input: str) -> dict:
    """Claude가 질문 분석"""
    
    prompt = f"""사용자의 음식점/카페 검색 요청을 분석해서 JSON으로 반환해.

                사용자 요청: "{user_input}"

                추출할 정보:
                - location: 기준 위치 (건물명, 주소, 역 등). 없으면 null
                - limit: 추천 개수. 언급 없으면 5
                - radius: 검색 반경(미터). 언급 없으면 500

                JSON만 반환. 다른 설명 없이.

                예시:
                "한라클래식 근처 점심 3개" → {{"location": "한라클래식", "limit": 3, "radius": 500}}
                "혼밥하기 좋은 곳" → {{"location": null, "limit": 5, "radius": 500}}"""

    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    
    try:
        raw = response.content[0].text
        print(f"[DEBUG] Claude 응답: {raw}")
        
        # 코드블록 제거
        clean = raw.replace("```json", "").replace("```", "").strip()
        
        result = json.loads(clean)
        return result
    except Exception as e:
        print(f"[DEBUG] 파싱 오류: {e}")  # 추가
        return {"location": None, "limit": 5, "radius": 500}


# ============================================================
# 7. AI 응답 생성
# ============================================================

def generate_response(user_input: str, places: list) -> str:
    """검색 결과로 자연스러운 응답 생성"""
    
    if not places:
        return "😅 조건에 맞는 곳을 찾지 못했어요."
    
    places_text = ""
    for i, p in enumerate(places, 1):
        dist = p.get('calculated_distance', p.get('distance', '?'))
        walk_min = max(1, int(dist) // 80) if str(dist).isdigit() else '?'
        
        places_text += f"""
                        [{i}] {p['name']}
                        - 카테고리: {p['category']}
                        - 거리: {dist}m (도보 약 {walk_min}분)
                        - 분위기: {', '.join(p.get('vibe', [])) or '정보 없음'}
                        - 추천 상황: {', '.join(p.get('situation', [])) or '정보 없음'}
                        - 주소: {p['address']}
                        - 전화: {p.get('phone') or '정보 없음'}
                        - 카카오맵: {p['url']}
                        """
    
    prompt = f"""사용자가 음식점/카페 추천을 요청했어.

                사용자 요청: "{user_input}"

                검색된 장소:
                {places_text}

                위 정보를 바탕으로 친절하게 추천해줘.
                - 분위기, 추천 상황 정보 활용
                - 카카오맵 링크 포함
                - 이모지 적절히 사용
                - 너무 길지 않게"""

    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text


# ============================================================
# 8. 메인 함수
# ============================================================

def chat(user_input: str) -> str:
    """
    자연어로 질문하면 벡터 검색 + AI 응답
    
    예시:
        chat("점심에 혼밥하기 좋은 곳")
        chat("데이트하기 좋은 분위기 있는 식당")
        chat("한라클래식 근처 조용한 카페 3개")
    """
    print(f"\n💬 질문: {user_input}")
    print("=" * 60)
    
    # 1️⃣ AI가 질문 파싱
    print("\n🤖 질문 분석 중...")
    parsed = parse_question(user_input)
    print(f"   → {parsed}")
    
    # 2️⃣ 벡터 검색 (의미 기반!)
    print("\n🔍 벡터 검색 중...")
    places = search_by_vector(user_input, limit=parsed.get("limit", 5) * 3)
    print(f"   → {len(places)}개 후보 발견")
    
    # 3️⃣ 위치 필터링 (있으면)
    if parsed.get("location"):
        coords = get_coordinates(parsed["location"])
        if coords:
            print(f"\n📍 위치 필터: {coords['name']}")
            
            for place in places:
                dist = calc_distance(
                    coords['y'], coords['x'],
                    float(place['y']), float(place['x'])
                )
                place['calculated_distance'] = dist
            
            # 반경 내 필터링
            radius = parsed.get("radius", 500)
            places = [p for p in places if p['calculated_distance'] <= radius]
            places.sort(key=lambda x: x['calculated_distance'])
            print(f"   → 반경 {radius}m 내 {len(places)}개")
    
    # 랜덤 셔플 (상위 결과 중에서)
    if len(places) > parsed.get("limit", 5):
        # 상위 유사도 중에서 랜덤 선택
        top_places = places[:parsed.get("limit", 5) * 2]
        random.shuffle(top_places)
        places = top_places[:parsed.get("limit", 5)]
    
    # 4️⃣ AI 응답 생성
    print("\n✍️ 응답 생성 중...")
    response = generate_response(user_input, places)
    
    print("\n" + "=" * 60)
    print(response)
    print("=" * 60)
    
    return response


# ============================================================
# 9. 실행
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            print("📋 아래 SQL을 Supabase SQL Editor에서 실행하세요:")
            print("=" * 50)
            print(SETUP_SQL)
            
        elif command == "store":
            store_places_with_tags()
            
        elif command == "chat":
            if len(sys.argv) > 2:
                user_input = " ".join(sys.argv[2:])
                chat(user_input)
            else:
                print("사용법: python script.py chat '질문'")
        
        else:
            print("""
                사용법:
                python gangnam_rag_free.py setup    # SQL 출력
                alias 설정(=단축키)
                echo "alias py11='/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11'" >> ~/.zshrc
                source ~/.zshrc
                -> py11 gangnam_rag_free.py store
                python gangnam_rag_free.py chat '질문'  # 질문하기

                예시:
                python gangnam_rag_free.py chat '점심에 혼밥하기 좋은 곳'
                python gangnam_rag_free.py chat '한라클래식 근처 데이트 식당 3개'
                """)
    
    else:
        print("🍽️ 강남 맛집 RAG (벡터 검색 버전)\n")
        chat("점심에 혼밥하기 좋은 한식 추천해줘")