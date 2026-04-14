"""
retriever.py
[LangChain] LangChain Retriever 래퍼 & Document 변환 유틸리티

기존 search_by_vector()를 LangChain이 인식할 수 있는 Retriever 인터페이스로 래핑한다. 
이 작업이 선행되어야 MultiQueryRetriever, ContextualCompressionRetriever,
EnsembleRetriever 같은 LangChain 생태계 기능을 쓸 수 있다.

구현 순서 추천:
    1. places_to_documents   — dict → Document 변환 먼저 (가장 단순)
    2. documents_to_places   — 역변환 (리랭킹 결과를 다시 기존 코드에 연결)
    3. build_supabase_retriever — BaseRetriever 서브클래스 생성
"""
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from search import search_by_vector
from pydantic import Field

# ============================================================
# [LangChain] Document 변환 유틸
# ============================================================

def places_to_documents(places: list) -> list:
    documents = []
    for place in places:
        doc = Document(
            page_content=place["content"],
            metadata = {
                k: v for k, v in place.items() if k != "content"
            }
        )
        documents.append(doc)
    return documents

# 음식점 document list -> dict list 변환
def documents_to_places(documents: list) -> list:
    places = []
    for doc in documents:
        place = dict(doc.metadata)
        place["content"] = doc.page_content
        places.append(place)
    return places
    

# ============================================================
# [LangChain] Supabase Retriever 래퍼
# ============================================================

class SupabaseRetriever(BaseRetriever):
    """Supabase pgvector 검색을 LangChain Retriever 인터페이스로 래핑"""

    k: int=20   # 검색할 후보 개수

    def _get_relevant_documents(self, query:str, *, run_manger:CallbackManagerForRetrieverRun) -> list[Document]:
        results = search_by_vector(query, limit=self.k)
        return places_to_documents(results)

def build_supabase_retriever(k: int = 20) -> SupabaseRetriever:
    """SupabaseRetriever 인스턴스를 생성해서 반환"""
    return SupabaseRetriever(k=k)