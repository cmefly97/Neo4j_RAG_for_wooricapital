"""
Hybrid 검색 진단 — 왜 hybrid 대신 키워드 폴백이 되는지 단계별 점검.
각 단계의 결과/예외(전체 traceback)를 로그에 남긴다.

실행: cd backend && python -m app.scripts.check_hybrid
"""
import sys
from app.scripts._runlog import run, log_exc

Q = "엔카 슬라이딩 가능해?"


def _body(log):
    try:
        from app.llm.embeddings import embedder
        from app.neo4j_client import client
        from app.search import hybrid
    except ModuleNotFoundError as e:
        log_exc(log, f"의존성 누락: {e.name}"); return 1

    log.info("embedder.is_available() = %s | base=%s model=%s",
             embedder.is_available(), embedder.base, embedder.model)
    try:
        qv = embedder.embed_one(Q)
        log.info("질의 임베딩 OK — 차원=%d", len(qv))
    except Exception:
        log_exc(log, "질의 임베딩 실패 (게이트웨이 /embeddings 확인)"); return 1

    # 인덱스 자동 탐지 결과
    vname, fname = hybrid.vector_index_name(), hybrid.fulltext_index_name()
    log.info("탐지된 인덱스 → VECTOR=%s, FULLTEXT=%s", vname, fname)
    log.info("hybrid.is_ready() = %s", hybrid.is_ready())

    if vname:
        try:
            vr = client.run_readonly(hybrid.vec_cypher(vname), {"k": 3, "qvec": qv})
            log.info("벡터 검색 %d건. 예: %s", len(vr),
                     [(r["source"], round(r["score"], 3)) for r in vr])
        except Exception:
            log_exc(log, "벡터 쿼리 실패")
    else:
        log.error("벡터 인덱스 미탐지 — :Chunk(embedding) ONLINE 벡터 인덱스 없음")

    if fname:
        lq = hybrid._lucene_query(Q)
        fr = client.run_readonly(hybrid.ft_cypher(fname), {"q": lq, "k": 3})
        log.info("풀텍스트(q=%r) %d건. 예: %s", lq, len(fr),
                 [(r["source"], round(r["score"], 3)) for r in fr])

    try:
        hr = hybrid.hybrid_retrieve(Q, k=3)
        log.info("hybrid_retrieve %d건 → %s", len(hr),
                 "정상" if hr else "빈 결과")
        for r in hr:
            log.info("   [%s/%s] score=%s", r["source"], r["locator"], r["score"])
    except Exception:
        log_exc(log, "hybrid_retrieve 실패"); return 1
    return 0


if __name__ == "__main__":
    sys.exit(run("check_hybrid", _body))
