"""
사용 가능한 LLM 레지스트리. 실제 .env 기반.
새 모델 추가는 MODELS에 항목 1개 추가로 끝난다.

provider:
  - "anthropic"     : Claude — Anthropic Messages API
  - "openai_compat" : 사내 게이트웨이(OpenAI 호환 /chat/completions) — HCX, Qwen 등
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


def _build_models() -> dict[str, "ModelSpec"]:
    # Qwen: 전용 값 없으면 HCX 게이트웨이/키 재사용
    qwen_base = settings.qwen_base_url or settings.hcx_base_url
    qwen_key = settings.qwen_api_key or settings.hcx_api_key
    return {
        "claude": ModelSpec(
            id="claude", provider="anthropic",
            label=f"Claude ({settings.anthropic_answer_model})",
            answer_model=settings.anthropic_answer_model,
            extract_model=settings.anthropic_extract_model,
            base_url=settings.anthropic_base_url,
            api_key=settings.anthropic_api_key,
        ),
        "hyperclova": ModelSpec(
            id="hyperclova", provider="openai_compat",
            label=f"HyperCLOVA X ({settings.hcx_answer_model})",
            answer_model=settings.hcx_answer_model,
            extract_model=settings.hcx_extract_model,
            base_url=settings.hcx_base_url,
            api_key=settings.hcx_api_key,
            supports_thinking=True,
        ),
        "qwen": ModelSpec(
            id="qwen", provider="openai_compat",
            label=f"Qwen ({settings.qwen_model})",
            answer_model=settings.qwen_model,
            extract_model=settings.qwen_model,
            base_url=qwen_base,
            api_key=qwen_key,
        ),
        "hcx30": ModelSpec(
            id="hcx30", provider="openai_compat",
            label=f"HCX-30B-Text ({settings.hcx30_model})",
            answer_model=settings.hcx30_model,
            extract_model=settings.hcx30_model,
            base_url=settings.hcx30_base_url,
            api_key=settings.hcx30_api_key,
            supports_thinking=True,
            # 사내 게이트웨이 thinking 모드 (curl 예시의 chat_template_kwargs)
            extra_body={"chat_template_kwargs": {"thinking": True}},
        ),
    }


MODELS = _build_models()
DEFAULT_MODEL_ID = "hcx30"   # 기준 베이스 모델: HCX-30B-Text (hcx-agent-05)


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
