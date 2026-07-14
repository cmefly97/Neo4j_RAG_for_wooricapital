"""
날짜별 로그 파일 + 사용자 액션 로깅.

- 로그 파일: backend/logs/YYYY-MM-DD.log (자정 기준 자동으로 파일 분리)
- 콘솔에도 동시 출력(uvicorn 터미널에서 즉시 확인 가능)
- log_action(action, **fields): 사용자 액션을 구조화 라인으로 기록
"""
import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_FMT = "%(asctime)s | %(levelname)-7s | %(message)s"


class DailyFileHandler(logging.Handler):
    """레코드 생성 시각 기준으로 logs/YYYY-MM-DD.log 에 기록."""
    def __init__(self, log_dir: Path):
        super().__init__()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            day = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d")
            line = self.format(record)
            with (self.log_dir / f"{day}.log").open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:  # noqa: BLE001
            self.handleError(record)


_logger: logging.Logger | None = None


def setup_logging() -> logging.Logger:
    global _logger
    if _logger:
        return _logger
    logger = logging.getLogger("woori_auto")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    fmt = logging.Formatter(_FMT)

    fileh = DailyFileHandler(LOG_DIR)
    fileh.setFormatter(fmt)
    consoleh = logging.StreamHandler()
    consoleh.setFormatter(fmt)

    logger.handlers.clear()
    logger.addHandler(fileh)
    logger.addHandler(consoleh)
    _logger = logger
    logger.info("STARTUP | logging initialized | dir=%s", LOG_DIR)
    return logger


def get_logger() -> logging.Logger:
    return _logger or setup_logging()


def _fmt_fields(fields: dict) -> str:
    parts = []
    for k, v in fields.items():
        s = str(v).replace("\n", " ")
        if len(s) > 500:
            s = s[:500] + "…"
        parts.append(f"{k}={s}")
    return " | ".join(parts)


def log_action(action: str, *, level: str = "INFO", **fields) -> None:
    """사용자 액션 1건 기록. 예: log_action('SEARCH', model='claude', q='...')"""
    msg = f"ACTION {action}"
    if fields:
        msg += " | " + _fmt_fields(fields)
    get_logger().log(getattr(logging, level.upper(), logging.INFO), msg)
