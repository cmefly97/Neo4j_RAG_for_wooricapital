"""질의 라우터 — 키워드 휴리스틱으로 질문 의도를 3분류 (doc-12 참고).

route:
  - "numeric"     수치 힌트만 → 결정적 테이블/정밀값 경로 우선
  - "mixed"       수치 + 규칙 힌트 → 하이브리드(테이블 보조 + 청크)
  - "descriptive" 수치 힌트 없음 → 청크 Hybrid+LLM

LLM 없이 동작(결정적). 게이트웨이 연결 시 LLM 분류 보강은 Phase 3.
"""
from __future__ import annotations

import re

# 수치 힌트 — 하나라도 있으면 has_num=True (소문자 비교)
# 주의: "점"은 "점검/점포" 등에 오매칭되므로 제외("933점" 같은 점수는 숫자로 이미 잡힘).
NUMERIC_HINTS = ("금리", "등급", "개월", "한도", "금액", "%",
                 "네고", "nego", "이자율", "프로모션")
# 규칙 힌트 — 하나라도 있으면 has_rule=True (원문 비교)
RULE_HINTS = ("가능", "까지", "판정", "슬라이딩", "대상", "여부", "취급")

_NUM_RE = re.compile(r"\d")


def route_intent(question: str) -> dict:
    q = question or ""
    ql = q.lower()

    num_hits = [h for h in NUMERIC_HINTS if h.lower() in ql]
    has_digit = bool(_NUM_RE.search(q))
    has_num = bool(num_hits) or has_digit

    rule_hits = [h for h in RULE_HINTS if h in q]
    has_rule = bool(rule_hits)

    if not has_num:
        route = "descriptive"
    elif has_rule:
        route = "mixed"
    else:
        route = "numeric"

    return {
        "route": route,
        "has_num": has_num,
        "has_rule": has_rule,
        "num_hits": num_hits + (["<숫자>"] if has_digit else []),
        "rule_hits": rule_hits,
    }
