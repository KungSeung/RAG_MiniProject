# 강남 맛집 RAG 시스템 (벡터 검색 버전)

자연어로 질문하면 AI가 강남 맛집/카페를 추천해주는 시스템입니다.

## 주요 기능

- 🔍 벡터 유사도 검색으로 의미 기반 검색 가능
- 🤖 Claude AI를 활용한 자연어 질문 파싱
- 📍 카카오맵 API로 위치 기반 필터링
- 💬 친절한 AI 응답 생성

## 설치 방법

### 1. 저장소 클론

```bash
git clone <your-repository-url>
cd find_rest_byrag
```

### 2. 가상 환경 생성 및 활성화

#### 방법 A: Conda 환경 (권장)

```bash
# 환경 생성
conda env create -f environment.yml

# 환경 활성화
conda activate data
```

#### 방법 B: Python venv

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 API 키를 설정하세요:

```bash
cp .env.example .env
```

`.env` 파일을 열어서 다음 값들을 입력하세요:

```env
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_service_role_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
KAKAO_API_KEY=KakaoAK your_kakao_rest_api_key_here
```

#### API 키 발급 방법

- **Supabase**: [https://supabase.com](https://supabase.com) → 프로젝트 생성 → Settings → API
- **Anthropic Claude**: [https://console.anthropic.com](https://console.anthropic.com) → API Keys
- **Kakao**: [https://developers.kakao.com](https://developers.kakao.com) → 내 애플리케이션 → REST API 키

## 사용 방법

### 1. Supabase 테이블 설정

```bash
python gangnam_rag_free.py setup
```

출력된 SQL을 복사하여 Supabase SQL Editor에서 실행하세요.

### 2. 데이터 저장

```bash
python gangnam_rag_free.py store
```

### 3. 질문하기

```bash
python gangnam_rag_free.py chat '점심에 혼밥하기 좋은 곳'
python gangnam_rag_free.py chat '한라클래식 근처 데이트 식당 3개'
python gangnam_rag_free.py chat '조용한 카페 추천해줘'
```

## Git 관리

### .gitignore 설정

`.gitignore` 파일이 자동으로 생성되어 있습니다. 다음 파일들은 Git에 추적되지 않습니다:

- `.env` (API 키 포함)
- `__pycache__/`
- 가상 환경 폴더
- IDE 설정 파일

### Git 저장소 초기화 및 커밋

```bash
# Git 저장소 초기화
git init

# 모든 파일 추가 (.gitignore에 의해 .env는 제외됨)
git add .

# 첫 커밋
git commit -m "Initial commit: 강남 맛집 RAG 시스템"

# GitHub 저장소 연결 (저장소 생성 후)
git remote add origin <your-github-repository-url>

# 푸시
git push -u origin main
```

## 프로젝트 구조

```
find_rest_byrag/
├── .env                          # API 키 (Git에 추적 안 됨)
├── .env.example                  # 환경 변수 예시
├── .gitignore                    # Git 제외 파일 목록
├── README.md                     # 프로젝트 설명
├── requirements.txt              # pip 패키지 목록
├── environment.yml               # conda 환경 설정
├── gangnam_rag_free.py          # 메인 코드
├── gangnam_places_with_tags.json # 데이터
└── kakao_crawl.py               # 크롤링 코드
```

## 보안 주의사항

⚠️ **절대로 `.env` 파일을 Git에 커밋하지 마세요!**

- API 키가 노출되면 악용될 수 있습니다
- `.gitignore`에 `.env`가 포함되어 있는지 확인하세요
- 실수로 커밋한 경우 즉시 API 키를 재발급하세요

## 라이선스

MIT License
