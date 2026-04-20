"""
prompts.py
프롬프트 템플릿 모음

[현재]
- 문자열 상수로 프롬프트 정의 (llm.py에서 import해서 사용)

[LangChain 업그레이드 예정]
- PromptTemplate / ChatPromptTemplate 버전으로 변환
- MessagesPlaceholder로 대화 기록 슬롯 추가
"""


# ============================================================
# 현재: 문자열 프롬프트
# ============================================================

PARSE_QUESTION_PROMPT = """사용자의 음식점/카페 검색 요청을 분석해서 JSON으로 반환해.

사용자 요청: "{user_input}"

추출할 정보:
- location: 기준 위치 (건물명, 주소, 역 등). 없으면 null
- limit: 추천 개수. 언급 없으면 5
- radius: 검색 반경(미터). 언급 없으면 500

JSON만 반환. 다른 설명 없이.

예시:
"한라클래식 근처 점심 3개" → {{"location": "한라클래식", "limit": 3, "radius": 500}}
"혼밥하기 좋은 곳" → {{"location": null, "limit": 5, "radius": 500}}"""


GENERATE_RESPONSE_PROMPT = """사용자가 음식점/카페 추천을 요청했어.

사용자 요청: "{user_input}"

검색된 장소:
{places_text}

위 정보를 바탕으로 친절하게 추천해줘.
- 분위기, 추천 상황 정보 활용
- 카카오맵 링크 포함
- 이모지 적절히 사용
- 너무 길지 않게"""

QUERY_EXPANSION_PROMPT = """너는 음식점/카페 검색 쿼리를 다양한 관점으로 확장하는 AI야.

사용자의 원본 질문을 보고, 같은 의도지만 다른 표현의 검색 쿼리 3개를 생성해.
각 쿼리는 줄바꿈으로 구분해서 출력해. 다른 설명 없이 쿼리만.

원본 질문: {question}
"""

from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# ============================================================
# [LangChain] PromptTemplate 버전
# ============================================================

# [LangChain - PromptTemplate] 질문 파싱용 템플릿
# 문자열 프롬프트를 LangChain PromptTemplate 객체로 래핑.
# 체인(|) 문법으로 LLM과 연결할 수 있게 해준다.

def get_parse_question_template():
    return PromptTemplate.from_template(PARSE_QUESTION_PROMPT)

# [LangChain - ChatPromptTemplate] 응답 생성용 대화 템플릿
# 대화 기록(chat_history)을 삽입할 수 있는 ChatPromptTemplate.
# 멀티턴 채팅에서 이전 대화를 참조하려면 MessagesPlaceholder가 필요.

def get_response_chat_template():
    return ChatPromptTemplate.from_messages(
        [
            ("system", "너는 강남 맛집/카페를 추천하는 AI야. 이전 대화 맥락을 참고해서 답변해."),
            MessagesPlaceholder("chat_history"), 
            ("human", GENERATE_RESPONSE_PROMPT)
        ]
    )

# [LangChain - PromptTemplate] 쿼리 확장용 템플릿 (MultiQueryRetriever 용)
# 하나의 질문을 여러 관점의 검색 쿼리로 확장할 때 쓰는 프롬프트.
# 예: "조용한 카페" → ["혼자 공부하기 좋은 카페", "소음 적은 카페", ...]

def get_query_expansion_template():
    return PromptTemplate.from_template(QUERY_EXPANSION_PROMPT)
