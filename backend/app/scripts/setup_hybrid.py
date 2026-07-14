"""
Hybrid 검색 준비 — 인덱스 확보(없으면 생성·ONLINE 대기) + 청크 임베딩 적재.

1) 풀텍스트 인덱스(cjk) on :Chunk(text)
2) 벡터 인덱스(cosine) on :Chunk(embedding)
3) embedding 없는 Chunk를 bge-m3로 임베딩해 채움

실행(사내망 + venv):
    cd backend && python -m app.scripts.setup_hybrid
    python -m app.scripts.setup_hybrid --reembed
로그: backend/logs/scripts_*.log
"""
import sys
from app.scripts._runlog import run, log_exc

FT_NAME = "chunkText"
VEC_NAME = "chunkVec"


def _body(log):
    try:
        from app.config import settings
        from app.neo4j_client import client
        from app.llm.embeddings import embedder
        from app.search import hybrid
    except ModuleNotFoundError as e:
        log_exc(log, f"의존성 누락: {e.name}")
        log.error("→ source ~/.venvs/jbwoori/bin/activate 후 재시도")
        return 1

    dim = int(settings.embed_dim)
    hybrid._cache.clear()
    ft, vec = hybrid.fulltext_index_name(), hybrid.vector_index_name()

    # 1) 없는 인덱스 생성
    created = []
    if ft:
        log.info("풀텍스트 인덱스 재사용: %s", ft)
    else:
        client.run(f"CREATE FULLTEXT INDEX {FT_NAME} IF NOT EXISTS "
                   "FOR (c:Chunk) ON EACH [c.text] "
                   "OPTIONS { indexConfig: { `fulltext.analyzer`: 'cjk' } }")
        created.append(FT_NAME)
    if vec:
        log.info("벡터 인덱스 재사용: %s", vec)
    else:
        client.run(f"CREATE VECTOR INDEX {VEC_NAME} IF NOT EXISTS "
                   "FOR (c:Chunk) ON c.embedding "
                   "OPTIONS { indexConfig: { "
                   f"`vector.dimensions`: {dim}, `vector.similarity_function`: 'cosine' }} }}")
        created.append(VEC_NAME)

    # 2) ONLINE 까지 대기 후 검증 (생성은 비동기 → 즉시 확인하면 POPULATING)
    if created:
        log.info("인덱스 생성 요청: %s — ONLINE 대기中", created)
        try:
            client.run("CALL db.awaitIndexes(300)")
        except Exception:  # noqa: BLE001  # 일부 버전 시그니처 차이
            log_exc(log, "db.awaitIndexes 경고(무시하고 재확인)")
        hybrid._cache.clear()
        ft, vec = hybrid.fulltext_index_name(), hybrid.vector_index_name()

    log.info("인덱스 상태 → 풀텍스트=%s, 벡터=%s", ft, vec)
    if not ft or not vec:
        log.error("인덱스 미탐지(ft=%s, vec=%s) — Neo4j 버전/문법 확인. "
                  "벡터는 프로시저 형식 시도: "
                  "CALL db.index.vector.createNodeIndex('chunkVec','Chunk','embedding',%d,'cosine')",
                  ft, vec, dim)
        return 1

    # 3) 임베딩 채우기
    if not embedder.is_available():
        log.error("임베딩 미설정 — .env EMBED_*/HCX_* 확인. 인덱스만 준비하고 종료."); return 1
    if "--reembed" in sys.argv:
        client.run("MATCH (c:Chunk) REMOVE c.embedding")
        log.info("기존 임베딩 제거(--reembed)")

    rows = client.run_readonly(
        "MATCH (c:Chunk) WHERE c.embedding IS NULL RETURN c.id AS id, c.text AS text")
    log.info("임베딩 대상 청크: %d", len(rows))
    if not rows:
        log.info("임베딩 최신 상태 — 추가 작업 없음"); return 0

    BATCH, done = 32, 0
    for i in range(0, len(rows), BATCH):
        part = rows[i:i + BATCH]
        vecs = embedder.embed([r["text"] or "" for r in part])
        client.run(
            "UNWIND $rows AS row MATCH (c:Chunk {id: row.id}) "
            "CALL db.create.setNodeVectorProperty(c, 'embedding', row.vec)",
            {"rows": [{"id": r["id"], "vec": v} for r, v in zip(part, vecs)]})
        done += len(part)
        log.info("  임베딩 진행 %d/%d", done, len(rows))
    log.info("임베딩 적재 완료: %d개", done)
    return 0


if __name__ == "__main__":
    sys.exit(run("setup_hybrid", _body))
