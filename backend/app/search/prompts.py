"""LLM 답변 경로의 프롬프트 룰 — 한곳에서 관리.

`cypher_qa.py`가 여기서 프롬프트를 가져다 쓴다. 답변 스타일·톤·근거 사용 규칙을
바꾸려면 이 파일만 수정한다. 전체 규칙 목록·근거는 `docs/14_답변규칙_카탈로그.md` 참조.
"""
from __future__ import annotations

# 답변 스타일(길이·상세도) — UI에서 선택. 기본 = standard
ANSWER_STYLES = {
    "standard": "정확하게 답변해줘.",
    "concise":  "정확하게, 핵심만 1~2문장으로 아주 간단히 답변해줘.",
    "detailed": ("정확하게 답변하되, 관련 조건·수치·등급·예외를 빠짐없이 "
                 "상담사가 설명하듯 완결된 문장(존댓말)으로 자세히 설명해줘."),
}
DEFAULT_ANSWER_MODE = "standard"

# 공통 골격: 상담 도우미 역할 + 근거만 사용 + 출처 명시
_ANSWER_TEMPLATE = (
    "너는 우리캐피탈 오토운영팀 상담을 돕는 도우미다. {style}\n"
    "아래 '자료'만 근거로 답하고, 자료에 없으면 지어내지 말 것. 끝에 출처 파일명을 밝혀라.\n"
    "반드시 한국어로만 답하라. 사고 과정(thinking)은 출력하지 말고 최종 답변만 한국어로 작성하라.\n\n"
    "[질문]\n{question}\n\n[자료]\n{context}\n\n[답변]"
)
ANSWER_PROMPTS = {m: _ANSWER_TEMPLATE.replace("{style}", s) for m, s in ANSWER_STYLES.items()}

# 전체 프롬프트를 직접 지정하는 모드(상담 보조원)
ANSWER_PROMPTS["counselor"] = (
    "너는 우리캐피탈 오토운영팀 상담 보조다. 반드시 제공된 근거에 근거해서만 답하라. "
    "근거에 없는 수치/사실은 만들지 말고 '규정에 명시되어 있지 않습니다'라고 답하라. "
    "반드시 한국어로만 답하고, 사고 과정(thinking)은 출력하지 말라. "
    "답변 끝에 출처를 밝혀라.\n\n[질문]\n{question}\n\n[자료]\n{context}\n\n[답변]"
)


def answer_prompt(mode: str | None) -> str:
    return ANSWER_PROMPTS.get(mode or DEFAULT_ANSWER_MODE, ANSWER_PROMPTS[DEFAULT_ANSWER_MODE])
