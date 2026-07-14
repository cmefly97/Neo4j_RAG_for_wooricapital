"""
API 엔드포인트 단위 테스트 (TestClient, run_search/Neo4j mock).

테스트 계획:
  GET /health            : 200 {status: ok}
  GET /models            : 2개 모델 반환, claude 기본
  POST /search           : run_search mock → 200 + 액션 로그(SEARCH_REQUEST/OK)
  POST /search 예외       : run_search 예외 → 500 {error:...} + SEARCH_ERROR 로그
  GET /admin/documents   : source_dir mock → 파일 목록
  POST /admin/upload     : 잘못된 확장자 → 400
"""
import datetime
import pytest
from fastapi.testclient import TestClient

import app.api.search as search_api
import app.api.admin as admin_api
from app.main import app
from app.logging_setup import LOG_DIR, get_logger

client = TestClient(app, raise_server_exceptions=False)


def _flush_logs():
    for h in get_logger().handlers:
        try: h.flush()
        except Exception: pass

def _today_log():
    _flush_logs()
    return (LOG_DIR / f"{datetime.date.today()}.log").read_text(encoding="utf-8")


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_models():
    r = client.get("/models")
    assert r.status_code == 200
    ms = r.json()["models"]
    assert any(m["id"] == "claude" and m["default"] for m in ms)


def test_search_ok_logs(monkeypatch):
    monkeypatch.setattr(search_api, "run_search",
        lambda q, m: {"answer": "ok", "cypher": "MATCH (n) RETURN n",
                      "rows": [{"n": 1}], "model_used": "Claude"})
    r = client.post("/search", json={"question": "테스트질문", "model": "claude"})
    assert r.status_code == 200
    log = _today_log()
    assert "SEARCH_REQUEST" in log and "SEARCH_OK" in log


def test_search_error_returns_500_and_logs(monkeypatch):
    def _boom(q, m): raise RuntimeError("boom")
    monkeypatch.setattr(search_api, "run_search", _boom)
    r = client.post("/search", json={"question": "에러유발"})
    assert r.status_code == 500
    assert "error" in r.json()
    assert "SEARCH_ERROR" in _today_log()


def test_documents_lists_files(monkeypatch, tmp_path):
    (tmp_path / "a.pdf").write_text("x")
    (tmp_path / "b.xlsx").write_text("x")
    (tmp_path / "ignore.txt").write_text("x")
    monkeypatch.setattr(admin_api.settings, "source_dir", str(tmp_path))
    r = client.get("/admin/documents")
    assert r.status_code == 200
    names = {d["name"] for d in r.json()["documents"]}
    assert names == {"a.pdf", "b.xlsx"}


def test_upload_rejects_bad_ext():
    r = client.post("/admin/upload",
                    files={"file": ("x.txt", b"data", "text/plain")})
    assert r.status_code == 400
