"""
LLM 연결 통합 테스트 (실 API 호출).
키/엔드포인트가 없거나 네트워크 도달 불가 시 자동 skip.

실행: cd backend && pytest tests/test_llm_connection.py -v -s
"""
import pytest

from app.llm import list_models, build_chat_model

PING = "연결 테스트입니다. 다른 말 없이 'OK'라고만 답하세요."

AVAILABLE = [m for m in list_models() if m["available"]]


@pytest.mark.parametrize("model", AVAILABLE, ids=[m["id"] for m in AVAILABLE])
def test_llm_responds(model):
    if not AVAILABLE:
        pytest.skip("사용 가능한 모델 없음(.env 키 미설정)")
    llm = build_chat_model(model["id"])
    try:
        resp = llm.invoke(PING)
    except Exception as e:  # noqa: BLE001
        low = (type(e).__name__ + str(e)).lower()
        if any(k in low for k in ("connect", "timeout", "resolve", "ssl", "network")):
            pytest.skip(f"엔드포인트 도달 불가(사내망/VPN 필요?): {e}")
        raise
    text = getattr(resp, "content", str(resp))
    assert text and len(text.strip()) > 0, "빈 응답"
