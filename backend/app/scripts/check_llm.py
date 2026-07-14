"""LLM 연결 점검 + 실행/에러 자동 로깅(backend/logs/scripts_*.log).

등록된(키 설정된) 모든 모델에 짧은 프롬프트를 보내 응답을 확인한다.
실행:
    cd backend && python -m app.scripts.check_llm
    cd backend && python -m app.scripts.check_llm claude       # 특정 모델만
종료코드: 0=하나라도 성공/건너뜀, 1=대상 전부 실패
"""
import sys
import time
from app.scripts._runlog import run, log_exc

PING = "연결 테스트입니다. 다른 말 없이 'OK'라고만 답하세요."


def check_one(log, model_id: str) -> bool:
    from app.llm import build_chat_model
    from app.llm.registry import get_model_spec
    spec = get_model_spec(model_id)
    log.info("[%s] id=%s provider=%s endpoint=%s model=%s",
             spec.label, spec.id, spec.provider, spec.base_url, spec.answer_model)
    try:
        llm = build_chat_model(model_id)
        t0 = time.time()
        resp = llm.invoke(PING)
        dt = time.time() - t0
        text = getattr(resp, "content", str(resp))
        log.info("[%s] ✅ 성공 (%.2fs) 응답=%r", spec.label, dt, text)
        return True
    except Exception as e:  # noqa: BLE001
        low = (type(e).__name__ + str(e)).lower()
        if any(k in low for k in ("connect", "timeout", "resolve", "ssl", "network")):
            hint = "네트워크/엔드포인트 도달 불가 (사내망/VPN 필요 가능성)"
        elif any(k in low for k in ("401", "403", "auth", "api key", "unauthorized")):
            hint = "인증 실패 (API 키 확인)"
        elif "404" in low or "model" in low:
            hint = "모델명/경로 확인"
        else:
            hint = ""
        log_exc(log, f"[{spec.label}] 실패: {type(e).__name__}")
        if hint:
            log.error("[%s] → %s", spec.label, hint)
        return False


def _body(log):
    try:
        from app.llm import list_models
    except ModuleNotFoundError as e:
        log_exc(log, f"의존성 누락: {e.name}")
        log.error("→ 해결: cd backend && pip install -r requirements.txt. 누락=%s", e.name)
        return 1

    only = sys.argv[1] if len(sys.argv) > 1 else None
    models = list_models()
    for m in models:
        log.info("등록 모델: %s (%s%s)", m["label"],
                 "사용가능" if m["available"] else "키 미설정",
                 ", 기본" if m["default"] else "")

    targets = [m for m in models if (only is None or m["id"] == only)]
    results = {}
    for m in targets:
        if not m["available"]:
            log.info("[%s] 건너뜀 — 키/엔드포인트 미설정", m["label"])
            results[m["id"]] = None
            continue
        results[m["id"]] = check_one(log, m["id"])

    for mid, ok in results.items():
        log.info("요약 %s: %s", mid, {True: "성공", False: "실패", None: "건너뜀"}[ok])
    failed = [v for v in results.values() if v is False]
    return 1 if (failed and not any(results.values())) else 0


if __name__ == "__main__":
    sys.exit(run("check_llm", _body))
