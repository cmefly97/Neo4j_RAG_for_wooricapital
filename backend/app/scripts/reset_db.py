"""
DB 완전 초기화 — 모든 노드/관계 + 인덱스/제약 삭제. (공유 DB의 영화 데이터·3072 인덱스 제거용)

⚠️ 되돌릴 수 없음. 우리 데이터는 ingest_source/setup_hybrid/build_structured 로 재생성 가능.
실수 방지: --yes 플래그 필수.

실행(사내망 + venv):
    cd backend
    python -m app.scripts.reset_db --yes
이후 재구축:
    python -m app.scripts.ingest_source
    python -m app.scripts.setup_hybrid
    python -m app.scripts.build_structured --model qwen
로그: backend/logs/scripts_*.log
"""
import sys
from app.scripts._runlog import run, log_exc


def _body(log):
    if "--yes" not in sys.argv:
        log.error("안전장치: 실제로 지우려면 --yes 를 붙이세요. "
                  "(예: python -m app.scripts.reset_db --yes)")
        return 1
    try:
        from app.neo4j_client import client
    except ModuleNotFoundError as e:
        log_exc(log, f"의존성 누락: {e.name}"); return 1

    # 0) 현황
    before = client.run_readonly("MATCH (n) RETURN count(n) AS c")[0]["c"]
    log.info("삭제 전 노드 수: %d", before)

    # 1) 제약 삭제
    cons = client.run_readonly("SHOW CONSTRAINTS YIELD name RETURN name")
    for c in cons:
        client.run(f"DROP CONSTRAINT {c['name']} IF EXISTS")
    log.info("제약 삭제: %d", len(cons))

    # 2) 인덱스 삭제 (LOOKUP=토큰 기본 인덱스는 보존)
    idx = client.run_readonly(
        "SHOW INDEXES YIELD name, type WHERE type <> 'LOOKUP' RETURN name, type")
    for ix in idx:
        client.run(f"DROP INDEX {ix['name']} IF EXISTS")
        log.info("  인덱스 삭제: %s (%s)", ix["name"], ix["type"])
    log.info("인덱스 삭제: %d", len(idx))

    # 3) 노드/관계 배치 삭제
    total = 0
    while True:
        r = client.run("MATCH (n) WITH n LIMIT 10000 DETACH DELETE n RETURN count(n) AS c")
        c = r[0]["c"] if r else 0
        total += c
        if c:
            log.info("  삭제 진행: 누적 %d", total)
        if c == 0:
            break

    after = client.run_readonly("MATCH (n) RETURN count(n) AS c")[0]["c"]
    log.info("초기화 완료 — 삭제 노드 %d, 남은 노드 %d", total, after)
    if after != 0:
        log.error("남은 노드가 0이 아님 — 확인 필요")
        return 1
    log.info("다음: ingest_source → setup_hybrid → build_structured 로 재구축")
    return 0


if __name__ == "__main__":
    sys.exit(run("reset_db", _body))
