"""
구조화 그래프 적재 — source 청크에서 LLM으로 엔티티/관계 추출 → Neo4j.

(:Entity {id,label,etype,source_file,origin:'structured', ...값속성})
(:Entity)-[:REL {relation, source_file, origin:'structured'}]->(:Entity)

실행(사내망 + venv):
    cd backend
    python -m app.scripts.build_structured                 # 전체
    python -m app.scripts.build_structured --limit 20      # 앞 20청크만(테스트)
    python -m app.scripts.build_structured --model hyperclova
주의: LLM 호출 다수(청크당 1회). thinking 모델은 느림 → --limit 로 먼저 확인 권장.
종료코드 0=정상. 로그: backend/logs/scripts_*.log
"""
import sys
from app.scripts._runlog import run, log_exc


def _arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def _body(log):
    try:
        from app.scripts.ingest_source import collect_chunks
        from app.ingestion.structured import extract_from_text
        from app.llm import build_chat_model
        from app.neo4j_client import client
    except ModuleNotFoundError as e:
        log_exc(log, f"의존성 누락: {e.name}")
        return 1

    model_id = _arg("--model")
    limit = int(_arg("--limit", "0"))
    chunks = collect_chunks()
    if limit:
        chunks = chunks[:limit]
    log.info("구조화 추출 대상 청크: %d (model=%s)", len(chunks), model_id or "default")

    try:
        llm = build_chat_model(model_id, role="extract")
    except Exception:  # noqa: BLE001
        log_exc(log, "LLM 생성 실패 — .env 키/모델 확인")
        return 1

    all_nodes, all_edges = {}, []
    for i, c in enumerate(chunks, 1):
        try:
            g = extract_from_text(c["text"], c["source_file"], llm)
        except Exception as e:  # noqa: BLE001
            log.warning("  [%d/%d] 추출 실패(건너뜀): %s", i, len(chunks), type(e).__name__)
            continue
        for n in g["nodes"]:
            all_nodes[n["id"]] = n        # id 기준 dedupe(교차청크 병합)
        all_edges += g["edges"]
        if i % 10 == 0 or i == len(chunks):
            log.info("  진행 %d/%d | 누적 노드 %d, 엣지 %d",
                     i, len(chunks), len(all_nodes), len(all_edges))

    nodes = list(all_nodes.values())
    log.info("추출 합계: 노드 %d, 엣지 %d", len(nodes), len(all_edges))
    if not nodes:
        log.warning("추출 결과 없음 — 종료")
        return 0

    # 멱등 재적재: 기존 structured 엔티티/관계만 제거(개념 그래프·청크는 보존)
    client.run("MATCH ()-[r:REL]-() WHERE r.origin='structured' DELETE r")
    client.run("MATCH (e:Entity) WHERE e.origin='structured' DETACH DELETE e")
    client.run("CREATE CONSTRAINT entity_id IF NOT EXISTS "
               "FOR (e:Entity) REQUIRE e.id IS UNIQUE")

    client.run(
        "UNWIND $rows AS n MERGE (e:Entity {id:n.id}) "
        "SET e += n.props, e.label=n.label, e.etype=n.etype, "
        "e.source_file=n.source_file, e.origin='structured'",
        {"rows": nodes})
    client.run(
        "UNWIND $rows AS x MATCH (a:Entity {id:x.source}) MATCH (b:Entity {id:x.target}) "
        "MERGE (a)-[r:REL {relation:x.relation}]->(b) "
        "SET r.source_file=x.source_file, r.origin='structured'",
        {"rows": all_edges})
    log.info("적재 완료: Entity=%d, REL=%d", len(nodes), len(all_edges))
    return 0


if __name__ == "__main__":
    sys.exit(run("build_structured", _body))
