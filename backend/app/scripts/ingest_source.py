"""
source/ 문서 → 그래프 데이터 → Neo4j 적재.

실행:
    cd backend
    python -m app.scripts.ingest_source                 # 결정적(청크) 적재 — 권장/기본
    python -m app.scripts.ingest_source --llm           # + LLM 엔티티 추출(사내망 필요)
    python -m app.scripts.ingest_source --dry            # 적재 없이 빌드 결과만 출력
"""
import sys
import glob
import unicodedata
from pathlib import Path

from app.config import settings
from app.ingestion.parsers import parse
from app.ingestion.extract import build_chunk_graph, extract_entities_llm

SKIP = ("온톨로지 및 에이전트",)  # 메모성 파일 제외(정답값 없음 → 검색 노이즈)
EXTS = (".md", ".docx", ".pdf", ".xlsx")


def collect_chunks() -> list[dict]:
    chunks = []
    src = settings.source_path
    print(f"  source 폴더: {src.resolve()} (존재={src.exists()})")
    for f in sorted(glob.glob(str(src / "*"))):
        if Path(f).suffix.lower() not in EXTS:
            continue
        # macOS 디스크 파일명은 NFD(분해형) → 코드의 NFC 문자열과 직접 비교 시 불일치.
        # 반드시 NFC 정규화 후 비교한다.
        fname = unicodedata.normalize("NFC", Path(f).name)
        if any(s in fname for s in SKIP):
            continue
        try:
            cs = parse(f)
            chunks += cs
            print(f"  파싱: {Path(f).name} → 청크 {len(cs)}")
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {Path(f).name}: {type(e).__name__}: {e}")
    if not chunks:
        print("  ⚠️ 파싱된 청크 0개 — source 폴더 경로/파일을 확인하세요 "
              "(.env SOURCE_DIR, 지원형식: md/docx/pdf/xlsx)")
    return chunks


def load_to_neo4j(graph: dict, llm_graph: dict | None):
    from app.neo4j_client import client
    nodes, edges = graph["nodes"], graph["edges"]
    docs = [n for n in nodes if n["_label"] == "Document"]
    chs = [n for n in nodes if n["_label"] == "Chunk"]

    client.run("CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
    client.run("CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE")
    # 재적재 멱등: 기존 Chunk/Document 제거 후 재생성
    client.run("MATCH (c:Chunk) DETACH DELETE c")
    client.run("MATCH (d:Document) DETACH DELETE d")

    client.run("UNWIND $rows AS d MERGE (x:Document {id:d.id}) "
               "SET x.name=d.name, x.source_file=d.source_file", {"rows": docs})
    client.run("UNWIND $rows AS c MERGE (x:Chunk {id:c.id}) "
               "SET x.text=c.text, x.source_file=c.source_file, x.locator=c.locator",
               {"rows": chs})
    client.run("UNWIND $rows AS e MATCH (c:Chunk {id:e.source}) MATCH (d:Document {id:e.target}) "
               "MERGE (c)-[:PART_OF]->(d)", {"rows": edges})
    print(f"적재: Document={len(docs)}, Chunk={len(chs)}, PART_OF={len(edges)}")

    if llm_graph and llm_graph["nodes"]:
        client.run("UNWIND $rows AS n MERGE (e:Entity {id:n.id}) "
                   "SET e.label=n.label, e.etype=n.etype, e.source_file=n.source_file",
                   {"rows": llm_graph["nodes"]})
        client.run("UNWIND $rows AS r MATCH (a:Entity {id:r.source}) MATCH (b:Entity {id:r.target}) "
                   "MERGE (a)-[x:REL {relation:r.relation}]->(b) SET x.source_file=r.source_file",
                   {"rows": llm_graph["edges"]})
        print(f"LLM 엔티티: nodes={len(llm_graph['nodes'])}, edges={len(llm_graph['edges'])}")


def main():
    use_llm = "--llm" in sys.argv
    dry = "--dry" in sys.argv
    print("=== source 파싱 ===")
    chunks = collect_chunks()
    graph = build_chunk_graph(chunks)
    print(f"\n빌드: 청크 {len(chunks)} → 노드 {len(graph['nodes'])} / 엣지 {len(graph['edges'])}")

    llm_graph = None
    if use_llm:
        print("\n=== LLM 엔티티 추출 (시간 소요) ===")
        llm_graph = extract_entities_llm(chunks)
        print(f"엔티티 {len(llm_graph['nodes'])}, 관계 {len(llm_graph['edges'])}")

    if dry:
        print("\n[--dry] 적재 생략. 샘플 청크:")
        for n in graph["nodes"][:3]:
            if n["_label"] == "Chunk":
                print(" ", n["locator"], "|", n["text"][:80].replace("\n", " "))
        return
    print("\n=== Neo4j 적재 ===")
    load_to_neo4j(graph, llm_graph)
    print("완료.")


if __name__ == "__main__":
    main()
