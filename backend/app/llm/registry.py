"""
사용 가능한 LLM 레지스트리. 실제 .env 기반.

현재는 기준 베이스 모델 **HCX-30B-Text(hcx-agent-06)** 하나만 운영한다.
(Claude·HyperCLOVA X·Qwen 등 다른 모델은 모델 관리 부담으로 제거됨 — 2026-07-20)
새 모델을 다시 추가하려면 MODELS에 항목 1개 추가로 끝난다.

provider:
  - "openai_compat" : 사내 게이트웨이(OpenAI 호환 /chat/completions) — HCX-30B-Text
"""
from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class ModelSpec:
    id: str
    provider: str            # "anthropic" | "openai_compat"
    label: str
    answer_model: str
    extract_model: str
    base_url: str
    api_key: str
    supports_thinking: bool = False
    extra_body: dict | None = None   # openai_compat 추가 요청 필드(예: chat_template_kwargs)
    max_tokens: int | None = None    # 지정 시 factory가 이 값을 사용(미지정 시 기본 로직)


def _build_models() -> dict[str, "ModelSpec"]:
    return {
        "hcx30": ModelSpec(
            id="hcx30", provider="openai_compat",
            label=f"HCX-30B-Text ({settings.hcx30_model})",
            answer_model=settings.hcx30_model,
            extract_model=settings.hcx30_model,
            base_url=settings.hcx30_base_url,
            api_key=settings.hcx30_api_key,
            supports_thinking=False,
            # thinking 비활성 + 최대 출력 토큰 1000 (사내 게이트웨이 chat_template_kwargs)
            extra_body={"chat_template_kwargs": {"thinking": False}},
            max_tokens=1000,
        ),
    }


MODELS = _build_models()
DEFAULT_MODEL_ID = "hcx30"   # 기준 베이스 모델: HCX-30B-Text (hcx-agent-06)


def _is_available(spec: ModelSpec) -> bool:
    if spec.provider == "anthropic":
        return bool(spec.api_key and spec.base_url)
    if spec.provider == "openai_compat":
        return bool(spec.api_key and spec.base_url)
    return False


def list_models() -> list[dict]:
    return [{
        "id": s.id, "label": s.label, "provider": s.provider,
        "available": _is_available(s), "default": s.id == DEFAULT_MODEL_ID,
    } for s in MODELS.values()]


def get_model_spec(model_id: str | None) -> ModelSpec:
    if not model_id:
        return MODELS[DEFAULT_MODEL_ID]
    if model_id not in MODELS:
        raise ValueError(f"알 수 없는 모델: {model_id}")
    return MODELS[model_id]
