"""
카카오 로컬 API를 활용한 강남역 음식점/카페 크롤링
+ Claude AI로 태그 자동 생성
"""

import requests
import json
import time
import os
from datetime import datetime
import anthropic
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


# ============================================================
# 1. 카카오 크롤러 (기존 코드)
# ============================================================

class KakaoLocalCrawler:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        self.headers = {"Authorization": f"kakaoAK {api_key}"}
    
        
    def search_places(
        self,
        query: str,
        x: str,
        y: str,
        radius: int = 500,
        category_group_code: str = None,
        page: int = 1,
        size: int = 15
    ) -> dict:
        params = {
            "query": query,
            "x": x,
            "y": y,
            "radius": radius,
            "page": page,
            "size": size,
            "sort": "distance"
        }
        
        if category_group_code:
            params["category_group_code"] = category_group_code
            
        response = requests.get(self.base_url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            print(f"API 오류: {response.status_code}")
            return None
            
        return response.json()
    
    def search_all_pages(
        self,
        query: str,
        x: str,
        y: str,
        radius: int = 500,
        category_group_code: str = None,
        max_pages: int = 10
    ) -> list:
        all_places = []
        
        for page in range(1, max_pages + 1):
            result = self.search_places(
                query=query, x=x, y=y, radius=radius,
                category_group_code=category_group_code, page=page
            )
            
            if not result or not result.get("documents"):
                break
                
            all_places.extend(result["documents"])
            
            if result["meta"]["is_end"]:
                break
                
            time.sleep(0.3)
            
        return all_places


# ============================================================
# 2. Claude 태그 생성기 (새로 추가!)
# ============================================================

class TagGenerator:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def generate_tags(self, name: str, category: str) -> dict:
        """
        음식점/카페 정보로 검색용 태그 생성
        
        입력: name="미진식당", category="음식점 > 한식 > 국수"
        출력: {
            "tags": ["점심", "식사", "면요리", "혼밥", "가벼운"],
            "meal_time": ["점심", "저녁"],
            "situation": ["혼밥", "간단한 식사"],
            "content": "미진식당은 한식 국수 전문점입니다. 점심 식사, 혼밥..."
        }
        """
        
        prompt = f"""음식점/카페 정보를 보고 검색용 태그를 생성해줘.

이름: {name}
카테고리: {category}

다음 JSON 형식으로만 응답해. 다른 설명 없이:

{{
    "tags": ["검색될 수 있는 키워드 10개 이상"],
    "meal_time": ["아침", "점심", "저녁", "야식" 중 해당하는 것],
    "situation": ["혼밥", "데이트", "회식", "가족모임", "친구모임", "비즈니스" 중 해당하는 것],
    "vibe": ["조용한", "활기찬", "캐주얼", "고급", "아늑한" 중 해당하는 것],
    "content": "이 장소를 설명하는 자연스러운 문장 (태그 키워드 포함, 3-4문장)"
}}

예시:
이름: 명동칼국수
카테고리: 음식점 > 한식 > 칼국수,만두

{{
    "tags": ["점심", "식사", "밥", "면", "칼국수", "만두", "한식", "국물", "따뜻한", "저렴한", "푸짐한"],
    "meal_time": ["점심", "저녁"],
    "situation": ["혼밥", "친구모임", "간단한 식사"],
    "vibe": ["캐주얼", "활기찬"],
    "content": "명동칼국수는 따뜻한 국물이 일품인 한식 칼국수 전문점입니다. 점심 식사나 간단한 저녁으로 좋으며, 혼밥하기에도 부담 없는 곳입니다. 칼국수와 만두를 함께 즐길 수 있어 푸짐한 한 끼를 원하는 분들께 추천합니다."
}}"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = json.loads(response.content[0].text)
            return result
            
        except Exception as e:
            print(f"  [오류] 태그 생성 실패: {e}")
            # 기본값 반환
            return {
                "tags": [],
                "meal_time": [],
                "situation": [],
                "vibe": [],
                "content": f"{name}은(는) {category} 전문점입니다."
            }


# ============================================================
# 3. 메인 크롤링 함수
# ============================================================

def crawl_with_tags():
    """크롤링 + 태그 생성"""

    # 환경 변수에서 API 키 로드
    KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    if not KAKAO_API_KEY or not ANTHROPIC_API_KEY:
        print("❌ 오류: .env 파일에서 API 키를 찾을 수 없습니다.")
        print("   KAKAO_API_KEY와 ANTHROPIC_API_KEY를 설정하세요.")
        return
    
    # 강남역 1번 출구 좌표
    GANGNAM_EXIT_1 = {"x": "127.0283", "y": "37.4979"}
    
    crawler = KakaoLocalCrawler(KAKAO_API_KEY)
    tag_generator = TagGenerator(ANTHROPIC_API_KEY)
    
    all_data = {
        "crawled_at": datetime.now().isoformat(),
        "location": "강남역 1번 출구",
        "coordinates": GANGNAM_EXIT_1,
        "restaurants": [],
        "cafes": []
    }
    
    # 음식점 카테고리
    restaurant_categories = [
        "한식", "중식", "일식", "양식", "분식",
        "치킨", "고기", "회", "찜", "국밥",
        "돈까스", "라멘", "파스타", "피자", "햄버거",
        "샐러드", "김밥", "포장마차", "술집"
    ]
    
    seen_ids = set()
    
    # ========== 1. 음식점 크롤링 ==========
    print("🍽️ 음식점 크롤링 중...")
    
    for category in restaurant_categories:
        print(f"  → {category} 검색 중...")
        places = crawler.search_all_pages(
            query=f"강남역 {category}",
            x=GANGNAM_EXIT_1["x"],
            y=GANGNAM_EXIT_1["y"],
            radius=500,
            category_group_code="FD6",
            max_pages=10
        )
        
        for place in places:
            if place["id"] in seen_ids:
                continue
            seen_ids.add(place["id"])
            
            all_data["restaurants"].append({
                "id": place["id"],
                "name": place["place_name"],
                "category": place["category_name"],
                "address": place["road_address_name"] or place["address_name"],
                "phone": place.get("phone", ""),
                "x": place["x"],
                "y": place["y"],
                "distance": place["distance"],
                "url": place["place_url"],
                # 태그는 아직 빈 값
                "tags": [],
                "meal_time": [],
                "situation": [],
                "vibe": [],
                "content": ""
            })
        
        print(f"     현재까지 {len(all_data['restaurants'])}개")
        time.sleep(0.5)
    
    print(f"\n  ✅ 총 {len(all_data['restaurants'])}개 음식점 수집 완료")
    
    # ========== 2. 카페 크롤링 ==========
    print("\n☕ 카페 크롤링 중...")
    cafes = crawler.search_all_pages(
        query="강남역 카페",
        x=GANGNAM_EXIT_1["x"],
        y=GANGNAM_EXIT_1["y"],
        radius=500,
        category_group_code="CE7",
        max_pages=5
    )
    
    cafe_ids = set()
    for place in cafes:
        if place["id"] in cafe_ids:
            continue
        cafe_ids.add(place["id"])
        
        all_data["cafes"].append({
            "id": place["id"],
            "name": place["place_name"],
            "category": place["category_name"],
            "address": place["road_address_name"] or place["address_name"],
            "phone": place.get("phone", ""),
            "x": place["x"],
            "y": place["y"],
            "distance": place["distance"],
            "url": place["place_url"],
            "tags": [],
            "meal_time": [],
            "situation": [],
            "vibe": [],
            "content": ""
        })
    
    print(f"  → {len(all_data['cafes'])}개 수집 완료")
    
    # ========== 3. AI 태그 생성 ==========
    print("\n🤖 AI 태그 생성 중...")
    
    total = len(all_data["restaurants"]) + len(all_data["cafes"])
    count = 0
    
    # 음식점 태그 생성
    for place in all_data["restaurants"]:
        count += 1
        print(f"  [{count}/{total}] {place['name']}...")
        
        tags = tag_generator.generate_tags(place["name"], place["category"])
        place["tags"] = tags.get("tags", [])
        place["meal_time"] = tags.get("meal_time", [])
        place["situation"] = tags.get("situation", [])
        place["vibe"] = tags.get("vibe", [])
        place["content"] = tags.get("content", "")
        
        time.sleep(0.5)  # API 부하 방지
    
    # 카페 태그 생성
    for place in all_data["cafes"]:
        count += 1
        print(f"  [{count}/{total}] {place['name']}...")
        
        tags = tag_generator.generate_tags(place["name"], place["category"])
        place["tags"] = tags.get("tags", [])
        place["meal_time"] = tags.get("meal_time", [])
        place["situation"] = tags.get("situation", [])
        place["vibe"] = tags.get("vibe", [])
        place["content"] = tags.get("content", "")
        
        time.sleep(0.5)
    
    print(f"\n  ✅ 태그 생성 완료!")
    
    # ========== 4. 저장 ==========
    all_data["restaurants"].sort(key=lambda x: int(x["distance"]))
    all_data["cafes"].sort(key=lambda x: int(x["distance"]))
    
    output_file = "gangnam_places_with_tags.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    total = len(all_data['restaurants']) + len(all_data['cafes'])
    print(f"\n✅ 저장 완료: {output_file}")
    print(f"   총 {total}개 장소 (음식점: {len(all_data['restaurants'])}, 카페: {len(all_data['cafes'])})")
    
    return all_data


# ============================================================
# 4. 기존 데이터에 태그만 추가 (크롤링 없이)
# ============================================================

def add_tags_to_existing(input_file: str = "gangnam_places.json"):
    """
    이미 크롤링한 데이터에 태그만 추가
    (크롤링 다시 안 해도 됨!)
    """

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    if not ANTHROPIC_API_KEY:
        print("❌ 오류: .env 파일에서 ANTHROPIC_API_KEY를 찾을 수 없습니다.")
        return

    tag_generator = TagGenerator(ANTHROPIC_API_KEY)
    
    # 기존 데이터 로드
    print(f"📂 {input_file} 로딩...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    total = len(data["restaurants"]) + len(data["cafes"])
    count = 0
    
    print(f"\n🤖 AI 태그 생성 중... (총 {total}개)")
    
    # 음식점 태그 생성
    for place in data["restaurants"]:
        count += 1
        print(f"  [{count}/{total}] {place['name']}...")
        
        tags = tag_generator.generate_tags(place["name"], place["category"])
        place["tags"] = tags.get("tags", [])
        place["meal_time"] = tags.get("meal_time", [])
        place["situation"] = tags.get("situation", [])
        place["vibe"] = tags.get("vibe", [])
        place["content"] = tags.get("content", "")
        
        time.sleep(0.5)
    
    # 카페 태그 생성
    for place in data["cafes"]:
        count += 1
        print(f"  [{count}/{total}] {place['name']}...")
        
        tags = tag_generator.generate_tags(place["name"], place["category"])
        place["tags"] = tags.get("tags", [])
        place["meal_time"] = tags.get("meal_time", [])
        place["situation"] = tags.get("situation", [])
        place["vibe"] = tags.get("vibe", [])
        place["content"] = tags.get("content", "")
        
        time.sleep(0.5)
    
    # 저장
    output_file = "gangnam_places_with_tags.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 저장 완료: {output_file}")
    
    return data


# ============================================================
# 5. 실행
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "tags-only":
        # 기존 데이터에 태그만 추가
        add_tags_to_existing("gangnam_places.json")
    else:
        # 전체 크롤링 + 태그 생성
        crawl_with_tags()