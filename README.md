# Gangnam Restaurant RAG System

자연어 질문 기반 강남역 맛집 추천 시스템.
벡터 유사도 검색과 위치 기반 필터링을 결합한 RAG(Retrieval-Augmented Generation) 파이프라인.

```
"한라클래식 근처 점심에 혼밥하기 좋은 곳 3개 추천해줘"
```

---

## Overview

일반 LLM에 맛집 추천을 요청하면 폐업한 가게를 추천하거나 존재하지 않는 식당을 생성하는 할루시네이션 문제가 발생한다.
해당 프로젝트는 RAG 아키텍처를 적용하여 실제 데이터베이스에서 검색한 결과를 기반으로 응답을 생성함으로써 이 문제를 해결한다.

### 처리 흐름

```
사용자 질문
    |
    v
[1] Claude API -- 질문 파싱 (위치, 개수, 반경 추출)
    |
    v
[2] ko-sroberta -- 질문을 768차원 벡터로 변환
    |
    v
[3] Supabase pgvector -- 코사인 유사도 기반 검색
    |
    v
[4] Kakao Local API -- 기준 위치 좌표 조회 + Haversine 거리 필터링
    |
    v
[5] Claude API -- 검색 결과 기반 자연어 응답 생성
```

---

## Tech Stack

| 구분      | 기술                                              |
| --------- | ------------------------------------------------- |
| Embedding | `jhgan/ko-sroberta-multitask` (768d, 한국어 특화) |
| Vector DB | Supabase + pgvector                               |
| LLM       | Claude API (Anthropic)                            |
| Geocoding | Kakao Local Search API                            |
| Language  | Python 3.11                                       |

---

## Project Structure

```
RAG_MiniProject/
├── gangnam_rag_free.py          # RAG 파이프라인 메인 코드
├── kakao_crawl.py               # 카카오 API 기반 맛집 데이터 수집
├── gangnam_places_with_tags.json # 태그 포함 맛집 데이터
├── environment.yml              # Conda 환경 설정
├── requirements.txt             # pip 의존성
├── .env.example                 # 환경 변수 템플릿
└── README.md
```

---

## Setup

### 1. 환경 구성

```bash
# Conda
conda env create -f environment.yml
conda activate rag

# 또는 pip
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example`을 복사하여 `.env` 파일을 생성하고 API 키를 입력한다.

```bash
cp .env.example .env
```

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
ANTHROPIC_API_KEY=your-anthropic-api-key
KAKAO_API_KEY=your-kakao-rest-api-key
```

### 3. 데이터베이스 초기화

Supabase SQL Editor에서 테이블 생성 SQL을 실행한다.

```bash
python gangnam_rag_free.py setup
```

출력되는 SQL을 Supabase 대시보드의 SQL Editor에 붙여넣고 실행한다. pgvector 확장 활성화, places 테이블 생성, 벡터 검색 함수 등록이 포함되어 있다.

### 4. 데이터 임베딩 및 저장

```bash
python gangnam_rag_free.py store
```

`gangnam_places_with_tags.json`의 음식점/카페 데이터를 읽어 임베딩을 생성하고 Supabase에 저장한다.

---

## Usage

```bash
python gangnam_rag_free.py chat '점심에 혼밥하기 좋은 한식 추천해줘'
python gangnam_rag_free.py chat '데이트하기 좋은 분위기 있는 식당'
python gangnam_rag_free.py chat '한라클래식 근처 조용한 카페 3개'
```

---

## Architecture Details

### 벡터 검색

단순 키워드 매칭이 아닌 의미 기반 검색을 수행한다. "혼밥"이라는 단어가 데이터에 없더라도, "1인식 가능", "카운터석", "혼자 와도 편한" 등의 태그와 의미적으로 유사하면 검색 결과에 포함된다.

각 장소의 content와 태그를 결합하여 임베딩을 생성한다.

```python
tags_text = " ".join(place.get("tags", []))
full_content = f"{content} {tags_text}"
embedding = get_embedding(full_content)
```

### 하이브리드 필터링

벡터 유사도로 넓게 후보를 확보한 뒤, 위치 조건이 있으면 Haversine 공식으로 거리를 계산하여 반경 내 결과만 필터링한다.

```
벡터 검색 (limit * 3배 후보 확보)
    |
    v
위치 조건 존재? -- Yes --> Kakao API로 좌표 조회 --> 반경 필터링
    |                                              |
    No                                             |
    |                                              v
    +----------------------<-----------------------+
    |
    v
상위 결과 중 랜덤 셔플 (동일 추천 방지)
    |
    v
최종 N개 반환
```

### 데이터 스키마

```sql
CREATE TABLE places (
    id bigserial PRIMARY KEY,
    place_id text UNIQUE NOT NULL,
    name text NOT NULL,
    category text,
    place_type text,         -- 'restaurant' | 'cafe'
    address text,
    phone text,
    x text,                  -- 경도
    y text,                  -- 위도
    tags text[],             -- ['혼밥', '가성비', '점심특선']
    meal_time text[],        -- ['점심', '저녁']
    situation text[],        -- ['데이트', '회식', '혼밥']
    vibe text[],             -- ['조용한', '모던한', '아늑한']
    content text,            -- 장소 설명 (임베딩 대상)
    embedding vector(768),   -- ko-sroberta 임베딩 벡터
    created_at timestamptz DEFAULT now()
);
```

---

## Known Issues / Improvements

### 보안

- Kakao API 인증 헤더 형식이 `KakaoAK {key}` 접두사 없이 사용되고 있음
- API 키가 코드 내에서 직접 참조되며, 추가적인 접근 제어 없음

### 에러 처리

- `parse_question`에서 Claude 응답 파싱 실패 시 기본값으로 silent fallback 발생
- Supabase 타임아웃, 카카오 API rate limit 등에 대한 방어 로직 부재
- 에러 로깅이 `print`로만 처리되어 프로덕션 디버깅에 부적합

### 성능

- `store_places_with_tags`에서 레코드를 1건씩 upsert하여 네트워크 호출 과다
- 벡터 검색 결과에 similarity threshold가 없어 낮은 유사도 결과가 포함될 수 있음

### 설계

- 임베딩 모델을 전역 변수 + lazy loading으로 관리하여 전역 상태 오염 가능성 존재
- Claude 모델 버전(`claude-sonnet-4-20250514`)이 하드코딩되어 있음
- 멀티턴 대화 미지원 (매 요청이 독립적)

---

## Roadmap

- [ ] 에러 처리 고도화 (타임아웃 재시도, rate limit 대응, 구조화된 로깅)
- [ ] 배치 upsert 적용으로 데이터 저장 성능 개선
- [ ] similarity threshold 도입으로 검색 품질 향상
- [ ] 리뷰 데이터 통합으로 임베딩 정밀도 개선
- [ ] Streamlit 기반 웹 인터페이스 구축
- [ ] 멀티턴 대화 지원
