"""단위 테스트 — 로깅/레지스트리/팩토리/청크빌드 (네트워크 불필요)."""
import datetime
import pytest

import app.config as cfg
from app.logging_setup import log_action, get_logger, LOG_DIR
from app.llm import registry, factory


def test_log_action_writes_dated_file():
    log_action("UNITTEST_ACTION", foo="bar", q="듀얼상품")
    for h in get_logger().handlers:
        try: h.flush()
        except Exception: pass
    f = LOG_DIR / f"{datetime.date.today()}.log"
    assert f.exists() and "ACTION UNITTEST_ACTION" in f.read_text(encoding="utf-8")


def test_list_models_has_hcx30_and_default():
    ms = registry.list_models()
    assert {"hcx30"} <= {m["id"] for m in ms}
    assert sum(1 for m in ms if m["default"]) == 1


def test_get_model_spec_default_and_invalid():
    assert registry.get_model_spec(None).id == "hcx30"
    with pytest.raises(ValueError):
        registry.get_model_spec("no-such-model")


def test_is_available_reflects_keys():
    from app.llm.registry import ModelSpec, _is_available
    def spec(provider, base_url, api_key):
        return ModelSpec(id="t", provider=provider, label="t", answer_model="m",
                         extract_model="m", base_url=base_url, api_key=api_key)
    # anthropic: 키 없으면 불가, 있으면 가능
    assert _is_available(spec("anthropic", "https://api.anthropic.com/v1/messages", "")) is False
    assert _is_available(spec("anthropic", "https://api.anthropic.com/v1/messages", "k")) is True
    # openai_compat: 키+base_url 둘 다 있어야 가능
    assert _is_available(spec("openai_compat", "", "k")) is False
    assert _is_available(spec("openai_compat", "https://gw/v1/chat/completions", "")) is False
    assert _is_available(spec("openai_compat", "https://gw/v1/chat/completions", "k")) is True


def test_anthropic_base_normalization():
    assert factory._anthropic_sdk_base("https://api.anthropic.com/v1/messages") is None
    assert factory._anthropic_sdk_base("https://gw.internal/v1/messages") == "https://gw.internal"


def test_openai_compat_base_normalization():
    assert factory._openai_compat_base(
        "https://namc-aigw.io.naver.com/v1/chat/completions") == "https://namc-aigw.io.naver.com/v1"


def test_build_chunk_graph():
    from app.ingestion.extract import build_chunk_graph
    chunks = [
        {"text": "취급 가능 개월수 12~72개월", "source_file": "a.pdf", "locator": "p1", "chunk_id": "c1"},
        {"text": "엔카 슬라이딩 조건", "source_file": "a.pdf", "locator": "p2", "chunk_id": "c2"},
    ]
    g = build_chunk_graph(chunks)
    docs = [n for n in g["nodes"] if n["_label"] == "Document"]
    chs = [n for n in g["nodes"] if n["_label"] == "Chunk"]
    assert len(docs) == 1 and len(chs) == 2
    assert all(e["type"] == "PART_OF" for e in g["edges"])
    assert any("12~72개월" in c["text"] for c in chs)
