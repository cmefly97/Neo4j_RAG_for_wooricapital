"""
model_id → LangChain Chat 모델 인스턴스 생성 (팩토리).
ModelSpec에 담긴 api_key/base_url/model 을 그대로 사용 → 새 모델 추가가 쉬움.

- anthropic     : ChatAnthropic (Anthropic Messages API)
- openai_compat : ChatOpenAI (사내 게이트웨이, OpenAI 호환) — HCX, Qwen
"""
from .registry import ModelSpec, get_model_spec


def _anthropic_sdk_base(url: str) -> str | None:
    """SDK는 host root를 받고 /v1/messages를 자동으로 붙인다. 표준 엔드포인트면 None."""
    if not url:
        return None
    root = url.split("/v1/")[0]
    if root.rstrip("/") == "https://api.anthropic.com":
        return None
    return root


def _openai_compat_base(url: str) -> str:
    """ChatOpenAI는 base_url 뒤에 /chat/completions를 붙인다. .../v1 로 정규화."""
    return url.split("/chat/completions")[0] if url else url


def build_chat_model(model_id: str | None = None, *, role: str = "answer",
                     temperature: float = 0.0, disable_extra_body: bool = False):
    """disable_extra_body=True → thinking 등 extra_body 미전달(빈 응답 재시도용)."""
    spec: ModelSpec = get_model_spec(model_id)
    model_name = spec.extract_model if role == "extract" else spec.answer_model
    # spec.max_tokens 지정 시 우선. 미지정이면 thinking 모델은 추론 토큰이 출력 한도를
    # 소비하므로 넉넉히(최종 답변이 빈 문자열로 잘리는 것 방지).
    max_tokens = spec.max_tokens or (8192 if spec.supports_thinking else 4096)

    if spec.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        kwargs = dict(model=model_name, api_key=spec.api_key,
                      temperature=temperature, max_tokens=max_tokens)
        base = _anthropic_sdk_base(spec.base_url)
        if base:
            kwargs["base_url"] = base
        return ChatAnthropic(**kwargs)

    if spec.provider == "openai_compat":
        from langchain_openai import ChatOpenAI
        kwargs = dict(
            model=model_name, api_key=spec.api_key,
            base_url=_openai_compat_base(spec.base_url),
            temperature=temperature, max_tokens=max_tokens,
        )
        # 추가 요청 필드(예: HCX thinking)는 OpenAI SDK의 extra_body로 감싸
        # 요청 JSON 본문 최상위에 실어 보낸다(curl의 chat_template_kwargs와 동일).
        if spec.extra_body and not disable_extra_body:
            kwargs["model_kwargs"] = {"extra_body": spec.extra_body}
        return ChatOpenAI(**kwargs)

    raise ValueError(f"지원하지 않는 provider: {spec.provider}")
