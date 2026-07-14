"""사용자 탭 API: 모델 목록 / 자연어 검색 / 노드 상세."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.search.cypher_qa import search as run_search, search_compare as run_compare
from app.llm import list_models
from app.neo4j_client import client
from app.logging_setup import log_action

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    question: str
    model: str | None = None          # 미지정 시 기본 모델
    answer_mode: str | None = None    # standard(기본) | concise(간단히) | detailed(자세히)


@router.get("/models")
def models():
    return {"models": list_models()}


@router.post("/search")
def search(req: SearchRequest):
    """반환: {answer, cypher, rows, model_used}"""
    log_action("SEARCH_REQUEST", model=req.model or "(default)",
               mode=req.answer_mode or "standard", q=req.question)
    try:
        result = run_search(req.question, req.model, req.answer_mode)
    except Exception as e:  # noqa: BLE001
        log_action("SEARCH_ERROR", level="ERROR", model=req.model or "(default)",
                   q=req.question, error=f"{type(e).__name__}: {e}")
        raise
    log_action("SEARCH_OK", model=result.get("model_used"),
               rows=len(result.get("rows", [])), cypher=result.get("cypher"))
    return result


@router.post("/search/compare")
def compare(req: SearchRequest):
    """벡터 전용 vs Hybrid 비교. 반환: {question, status, vector, hybrid}"""
    log_action("COMPARE_REQUEST", model=req.model or "(default)",
               mode=req.answer_mode or "standard", q=req.question)
    try:
        result = run_compare(req.question, req.model, req.answer_mode)
    except Exception as e:  # noqa: BLE001
        log_action("COMPARE_ERROR", level="ERROR", model=req.model or "(default)",
                   q=req.question, error=f"{type(e).__name__}: {e}")
        raise
    log_action("COMPARE_OK", status=result.get("status"))
    return result


@router.get("/node/{node_id}")
def node(node_id: str):
    log_action("NODE_DETAIL", node_id=node_id)
    rows = client.run_readonly(
        "MATCH (e:Entity {id: $id}) "
        "OPTIONAL MATCH (e)-[r:REL]-(n:Entity) "
        "RETURN e AS node, collect({relation: r.relation, neighbor: n.label, "
        "neighbor_id: n.id}) AS edges",
        {"id": node_id},
    )
    if not rows:
        raise HTTPException(404, "노드를 찾을 수 없습니다.")
    return rows[0]
