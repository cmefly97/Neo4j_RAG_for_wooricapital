"""FastAPI 엔트리포인트 — 우리캐피탈 오토운영팀 KG 검색 PoC."""
import time
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, search
from app.logging_setup import setup_logging, get_logger

logger = setup_logging()

app = FastAPI(title="Woori Auto KG Search (PoC)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    # localhost 의 어떤 포트(5173/5174 등)에서도 허용 — 포트 불일치로 인한 CORS 차단 방지
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 요청을 날짜별 로그에 기록(메서드/경로/상태/소요시간)."""
    t0 = time.time()
    try:
        resp = await call_next(request)
    except Exception:  # noqa: BLE001
        dt = (time.time() - t0) * 1000
        logger.error("REQ %s %s | ERROR %.0fms\n%s",
                     request.method, request.url.path, dt, traceback.format_exc())
        raise
    dt = (time.time() - t0) * 1000
    logger.info("REQ %s %s | %s | %.0fms",
                request.method, request.url.path, resp.status_code, dt)
    return resp


@app.exception_handler(Exception)
async def unhandled_exc(request: Request, exc: Exception):
    """미처리 예외를 로그에 남기고 JSON 에러로 응답(프론트에서 표시 가능)."""
    get_logger().error("UNHANDLED %s %s | %s: %s",
                        request.method, request.url.path,
                        type(exc).__name__, exc)
    return JSONResponse(status_code=500,
                        content={"error": f"{type(exc).__name__}: {exc}"})


app.include_router(admin.router)
app.include_router(search.router)


@app.get("/health")
def health():
    return {"status": "ok"}
