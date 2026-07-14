"""결정적(테이블) 답변 경로의 정책·템플릿 룰 — 한곳에서 관리.

`tables.py`(로직)는 여기 정의된 **정책 플래그**와 **문장 템플릿**만 참조한다.
규칙 변경(문구·포맷·정책)은 이 파일만 수정하면 되고, 조회/파싱 로직은 건드리지 않는다.
전체 규칙 목록·근거는 `docs/14_답변규칙_카탈로그.md` 참조.
"""
from __future__ import annotations

# ── 정책 플래그 (동작 규칙) ─────────────────────────────────────────────
# 고객유형 미지정 시 데이터가 있는 유형(내국인·외국인)을 모두 답변에 포함
SHOW_BOTH_CUSTOMERS = True
# 개월수 미지정 시 전체 개월 금리를 나열(지정 시 해당 구간 1건)
LIST_TERMS = True
# 최저금리라도 'G/L − 네고' 산술을 하지 않고 G/L + 적용가능 네고 목록만 제시
NEGO_ARITHMETIC = False
# 질문에 명시된 네고(거점장·증빙·HJ)만 필터링(미명시 시 전체)
NEGO_FILTER_BY_QUERY = True
# 프로모션은 모든 기준(금리등급·NICE·KCB)을 충족해야 가능으로 판정
PROMO_REQUIRE_ALL = True
# 답변 끝에 출처 파일명 표기
SHOW_SOURCES = True

# 필터 대상 네고 명칭
NEGO_NAMES = ("거점장", "증빙", "HJ")
# 프로모션 판정 항목 라벨
KIND_LABEL = {"grade": "금리등급", "nice": "NICE", "kcb": "KCB"}

# ── 금리등급/네고 답변 템플릿 ───────────────────────────────────────────
RATE_BLOCK = "{ct} 일 시 금리등급 {grade}등급 기준 금리는 {rate_str} 입니다."
RATE_NEGO_SUFFIX = " {nstr} 네고 가능합니다"
TERM_ITEM = "{months}개월 {rate}"          # 개월별 금리 항목
NEGO_ITEM = "{type} {rate}"                # 네고 항목

# ── 프로모션 답변 템플릿 ────────────────────────────────────────────────
PROMO_CRIT_GRADE = "금리등급 {v}등급"
PROMO_CRIT_NICE = "NICE {v}점 이상"
PROMO_CRIT_KCB = "KCB {v}점 이상"
PROMO_BASE = "프로모션은 {crit}을(를) 모두 충족해야 G/L 금리 {rate}가 적용됩니다{tail}."
PROMO_FAIL = "아니요, 불가능합니다. {base} 입력하신 값 중 {fails}이(가) 기준에 미달합니다."
PROMO_UNKNOWN = "입력하신 값({passes})은 기준을 충족합니다. 다만 {unknowns} 조건도 함께 확인되어야 합니다. {base}"
PROMO_PASS = "네, 가능합니다. {base}"
PROMO_FAIL_ITEM = "{label} {valstr}(기준 {thrstr})"
PROMO_LIST_ITEM = "{crit}을(를) 모두 충족할 경우 G/L 금리 {rate} 적용{tail}"
PROMO_LIST_HEADER = "프로모션 기준은 다음과 같습니다.\n- "
PROMO_EXCLUDE_TAIL = "({exclude} 제외)"       # 값 판정 시(문장 중간)
PROMO_EXCLUDE_TAIL_SP = " ({exclude} 제외)"   # 기준 나열 시(공백 포함)
