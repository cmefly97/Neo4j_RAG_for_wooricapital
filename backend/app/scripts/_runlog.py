"""스크립트 실행/에러 자동 로깅 헬퍼 — stdlib만 사용(import 실패하지 않음).

각 테스트/점검 스크립트의 실행 시작·종료·예외(전체 traceback)를
backend/logs/scripts_YYYY-MM-DD.log 에 append하고 콘솔에도 출력한다.
목적: 다음 실행에서 에러가 나면 이 로그만 보고 바로 디버깅한다.

사용:
    from app.scripts._runlog import run, log_exc
    def _body(log):     # log = logging.Logger
        ...             # return 0/1 (종료코드)
    if __name__ == "__main__":
        import sys; sys.exit(run("스크립트이름", _body))
"""
from __future__ import annotations
import logging
import sys
import datetime
import traceback
from pathlib import Path


def _log_dir() -> Path:
    # 이 파일: backend/app/scripts/_runlog.py → parents[2] = backend
    d = Path(__file__).resolve().parents[2] / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_logger(name: str) -> logging.Logger:
    log = logging.getLogger(f"script.{name}")
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    fp = _log_dir() / f"scripts_{datetime.date.today():%Y-%m-%d}.log"
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                            "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(fp, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(sh)
    log.info("LOGFILE %s", fp)
    return log


def log_exc(log: logging.Logger, msg: str) -> None:
    """전체 traceback을 로그파일+콘솔에 남긴다."""
    log.error("%s\n%s", msg, traceback.format_exc())


def run(name: str, fn) -> int:
    """fn(log) 실행을 감싸 시작/종료/예외를 로깅하고 종료코드를 반환."""
    log = get_logger(name)
    log.info("START %s | argv=%s", name, sys.argv[1:])
    try:
        rc = fn(log)
        rc = 0 if rc is None else int(rc)
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else (0 if not e.code else 1)
        log.info("SystemExit rc=%s", rc)
    except BaseException:  # noqa: BLE001  # KeyboardInterrupt 포함 전부 기록
        log_exc(log, f"{name} 미처리 예외")
        rc = 1
    log.info("END %s rc=%s", name, rc)
    return rc
