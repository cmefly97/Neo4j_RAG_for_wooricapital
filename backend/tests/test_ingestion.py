"""
적재 파이프라인 테스트 — source 경로 해석 / 청크 수집 / Neo4j 적재 호출.
(이전 버그: backend/에서 './source'가 backend/source를 가리켜 청크 0개)
"""
import app.scripts.ingest_source as ing
from app.config import settings
from app.ingestion.extract import build_chunk_graph


def test_source_path_resolves_regardless_of_cwd():
    """cwd가 backend/ 여도 프로젝트 루트의 source 폴더를 찾아야 한다."""
    sp = settings.source_path
    assert sp.exists(), f"source 폴더 없음: {sp}"
    files = [f for f in sp.glob("*") if f.suffix.lower() in (".pdf", ".md", ".docx", ".xlsx")]
    assert files, "source 폴더에 지원 문서가 없음"


def test_collect_chunks_nonempty():
    chunks = ing.collect_chunks()
    assert len(chunks) > 0, "청크 0개 — 경로/파싱 문제"
    assert all("text" in c and "source_file" in c and "chunk_id" in c for c in chunks)


def test_load_to_neo4j_sends_nonempty_rows(monkeypatch):
    """load_to_neo4j 가 Document/Chunk를 비어있지 않은 rows로 MERGE 호출하는지."""
    import app.neo4j_client as nc
    calls = []

    class FakeClient:
        def run(self, cypher, params=None):
            calls.append((cypher, params))
            return []

    monkeypatch.setattr(nc, "client", FakeClient())
    chunks = [
        {"text": "엔카 슬라이딩 조건", "source_file": "a.pdf", "locator": "p1", "chunk_id": "c1"},
        {"text": "취급 가능 개월수 12~72개월", "source_file": "a.pdf", "locator": "p2", "chunk_id": "c2"},
    ]
    graph = build_chunk_graph(chunks)
    ing.load_to_neo4j(graph, None)

    doc_calls = [c for c in calls if "MERGE (x:Document" in c[0]]
    chunk_calls = [c for c in calls if "MERGE (x:Chunk" in c[0]]
    assert doc_calls and doc_calls[0][1]["rows"], "Document rows 비어있음"
    assert chunk_calls and len(chunk_calls[0][1]["rows"]) == 2, "Chunk rows 누락"


def test_full_pipeline_builds_chunks_from_real_source():
    """실제 source 파싱 → 빌드까지 (Neo4j 없이) 청크/문서 노드 생성 확인."""
    chunks = ing.collect_chunks()
    graph = build_chunk_graph(chunks)
    chs = [n for n in graph["nodes"] if n["_label"] == "Chunk"]
    docs = [n for n in graph["nodes"] if n["_label"] == "Document"]
    assert len(chs) == len(chunks) and len(docs) >= 1
    # 정답 텍스트가 청크에 실제로 들어있는지(핵심 키워드)
    blob = "\n".join(c["text"] for c in chs)
    assert any(k in blob for k in ("개월", "슬라이딩", "Dual", "R판정"))
