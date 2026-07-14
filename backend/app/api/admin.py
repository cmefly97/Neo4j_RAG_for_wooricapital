"""관리자 탭 API: 업로드 / 문서리스트 / 재처리 / 삭제 / 그래프 뷰."""
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import settings
from app.neo4j_client import client
from app.logging_setup import log_action

router = APIRouter(prefix="/admin", tags=["admin"])

ALLOWED = {".xlsx", ".docx", ".pdf", ".md"}


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED:
        log_action("UPLOAD_REJECT", level="WARNING", file=file.filename, reason="형식")
        raise HTTPException(400, f"허용 형식: {sorted(ALLOWED)}")
    dest = settings.source_path / file.filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    log_action("UPLOAD", file=file.filename, type=ext.lstrip("."))
    # TODO: 비동기 파이프라인 트리거
    return {"filename": file.filename, "status": "uploaded", "next": "pending_ingestion"}


@router.get("/documents")
def documents():
    src = settings.source_path
    if not src.exists():
        return {"documents": []}
    files = [
        {"name": p.name, "type": p.suffix.lower().lstrip("."),
         "size": p.stat().st_size, "status": "completed"}
        for p in src.glob("*") if p.suffix.lower() in ALLOWED
    ]
    log_action("DOCUMENTS_LIST", count=len(files))
    return {"documents": files}


@router.post("/documents/{doc_id}/reprocess")
def reprocess(doc_id: str):
    log_action("REPROCESS", doc=doc_id)
    return {"doc_id": doc_id, "status": "reprocess_queued"}


@router.delete("/documents/{doc_id}")
def delete(doc_id: str):
    client.run("MATCH ()-[r:REL]-() WHERE r.source_file CONTAINS $doc DELETE r",
               {"doc": doc_id})
    client.run("MATCH (e:Entity) WHERE e.source_file CONTAINS $doc AND NOT (e)--() DELETE e",
               {"doc": doc_id})
    f = settings.source_path / doc_id
    if f.exists():
        f.unlink()
    log_action("DELETE", doc=doc_id)
    return {"doc_id": doc_id, "status": "deleted"}


@router.get("/graph")
def graph(doc_id: str | None = None):
    where = "WHERE e.source_file CONTAINS $doc" if doc_id else ""
    nodes = client.run(
        f"MATCH (e:Entity) {where} "
        "RETURN e.id AS id, e.label AS label, e.community AS community, "
        "e.source_file AS source_file LIMIT 500",
        {"doc": doc_id} if doc_id else None,
    )
    edges = client.run(
        "MATCH (s:Entity)-[r:REL]->(t:Entity) "
        "RETURN s.id AS source, t.id AS target, r.relation AS relation, "
        "r.confidence AS confidence LIMIT 1000"
    )
    log_action("GRAPH_VIEW", doc=doc_id or "(all)", nodes=len(nodes), edges=len(edges))
    return {"nodes": nodes, "edges": edges}
