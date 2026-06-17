from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(
    prefix="/rag",
    tags=["Enterprise RAG"]
)

class ChatQuery(BaseModel):
    company_id: int
    query: str

@router.post("/chat")
def consult_ceo(req: ChatQuery):
    """
    RAG-based chat endpoint.
    1. Embed the query using an embedding model.
    2. Search pgvector for similar past meetings, sales data, and contacts.
    3. Feed context + query to Claude/GPT.
    4. Return strategic advice.
    """

    # Mock Response based on query
    if "매출" in req.query or "수주" in req.query:
        answer = "최근 영업 미팅록(ABC Corp)과 재무 데이터를 분석한 결과, 제안서 발송 후 후속 조치(Follow-up)가 1주일 이상 지연되었을 때 수주 실패율이 높아집니다. 이번 주 대기 중인 500,000원(XYZ Inc) 건에 대해 즉시 후속 미팅을 잡는 것을 권장합니다."
    elif "컨디션" in req.query:
        answer = "지난주 미팅록 감성 분석 결과, 팀원들의 긍정적인 언어 사용 빈도가 15% 상승했습니다. 특히 새로운 ERP 프로젝트 도입 후 행정 업무 스트레스가 줄어든 것으로 파악됩니다."
    else:
        answer = "질문하신 내용에 대한 사내 데이터를 기반으로 분석 중입니다. 더 구체적으로 말씀해 주시면 정확한 경영 전략을 제안해 드릴 수 있습니다."

    return {
        "query": req.query,
        "answer": answer,
        "sources_used": ["meetings_db", "finance_db"]
    }
