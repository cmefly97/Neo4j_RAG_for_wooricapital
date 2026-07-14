"""Neo4j 동작 점검 + 실행/에러 자동 로깅(backend/logs/scripts_*.log).

연결되면 노드 통계 출력, 안 되면 원인 진단 + 전체 traceback 로깅.
실행: cd backend && python -m app.scripts.check_neo4j
종료코드: 0=정상, 1=실패
"""
import sys
from app.scripts._runlog import run, log_exc


def _body(log):
    # 1) 의존성/설정 로드 (여기서 죽으면 보통 'pip install -r requirements.txt' 누락)
    try:
        from app.config import settings
    except ModuleNotFoundError as e:
        log_exc(log, f"의존성 누락: {e.name}")
        log.error("→ 해결: cd backend && pip install -r requirements.txt "
                  "(가상환경 사용 시 먼저 활성화). 누락 모듈=%s", e.name)
        return 1
    except Exception:  # noqa: BLE001
        log_exc(log, "설정 로드 실패(.env/config)")
        return 1

    log.info("대상 Neo4j: %s (user=%s)", settings.neo4j_uri, settings.neo4j_user)

    # 2) 연결 + 노드 통계
    try:
        from app.neo4j_client import client
        client.run("RETURN 1")
        stats = {}
        for label in ("Entity", "Chunk", "Document"):
            r = client.run(f"MATCH (n:{label}) RETURN count(n) AS n")
            stats[label] = r[0]["n"] if r else 0
        log.info("연결 정상 | Entity=%s Chunk=%s Document=%s",
                 stats["Entity"], stats["Chunk"], stats["Document"])
        if stats["Chunk"] == 0 and stats["Entity"] == 0:
            log.warning("적재 데이터 없음 → `python -m app.scripts.ingest_source` "
                        "또는 `load_graph_json ../graph_output/graph.json` 실행")
        return 0
    except Exception as e:  # noqa: BLE001
        log_exc(log, f"Neo4j 연결 실패: {type(e).__name__}")
        log.error("[점검] 1) nc -z -w5 <host> 7687  2) .env URI/USER/PASSWORD  "
                  "3) 방화벽/사내망(VPN) IP:7687 허용  4) TLS면 bolt+s://|neo4j+s://")
        return 1


if __name__ == "__main__":
    sys.exit(run("check_neo4j", _body))
