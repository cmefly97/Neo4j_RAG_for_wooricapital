"""수치형 질의용 결정적 테이블 조회 + 템플릿 답변 (LLM/Neo4j 무의존).

doc-12 참고: 금리등급/네고/프로모션 같은 수치형 질의는 깨지기 쉬운 PDF 표 청크를
LLM에 해석시키는 대신, 큐레이션된 CSV(backend/data/*.csv)에서 값을 뽑아
파이썬 템플릿으로 문장을 조립한다 → 빈응답·환각 원천 제거, 결정적.

이 파일은 **로직(파싱·조회·조립)** 만 담는다. 문장 템플릿·동작 정책은
`answer_rules.py`(R)에서 참조하며, 규칙 변경은 그 파일만 수정한다.

핵심 진입점: answer_numeric(question) -> dict | None
  - 답을 만들 수 있으면 {"answer", "sources", "facts", "matched"} 반환
  - 해당 없으면 None (호출측은 기존 Hybrid+LLM 경로로 폴백)
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from app.search import answer_rules as R

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load(name: str) -> list[dict]:
    p = _DATA_DIR / f"{name}.csv"
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _int(v, default=None):
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return default


# ---------- 조회 ----------

def lookup_promotion() -> list[dict]:
    return _load("promotion")


def lookup_rates(grade: int, customer_type: str) -> list[dict]:
    """등급+고객유형의 모든 금리 행(개월 오름차순). 외국인은 개월별 여러 행일 수 있음."""
    rows = [r for r in _load("rate_grade")
            if _int(r.get("grade")) == grade
            and (r.get("customer_type") or "").strip() == customer_type]
    rows.sort(key=lambda r: _int(r.get("term_min_months"), 0))
    return rows


def available_customers(grade: int) -> list[str]:
    """해당 등급에 데이터가 있는 고객유형(내국인→외국인 순)."""
    rows = _load("rate_grade")
    out = []
    for ct in ("내국인", "외국인"):
        if any(_int(r.get("grade")) == grade and (r.get("customer_type") or "").strip() == ct
               for r in rows):
            out.append(ct)
    return out


def lookup_nego(grade: int, customer_type: str | None = None) -> list[dict]:
    out = []
    for r in _load("nego_rule"):
        lo, hi = _int(r.get("grade_from")), _int(r.get("grade_to"))
        if lo is None or hi is None or not (lo <= grade <= hi):
            continue
        ct = (r.get("customer_type") or "").strip()
        if customer_type and ct not in ("", customer_type):
            continue
        out.append(r)
    return out


# ---------- 질의 파싱 ----------

_GRADE_RE = re.compile(r"(\d+)\s*등급")
_TERM_RE = re.compile(r"(\d+)\s*개월")
# 사용자가 질문에 적은 신용점수 (기준값이 아니라 '내 값')
_NICE_RE = re.compile(r"(?:나이스|nice)\s*(\d{2,4})", re.I)
_KCB_RE = re.compile(r"(?:kcb|케이씨비|올크레딧|올크레딧점수)\s*(\d{2,4})", re.I)


def _user_values(q: str) -> dict:
    """질문에서 사용자가 제시한 값(금리등급/NICE/KCB) 추출."""
    g = _GRADE_RE.search(q)
    n = _NICE_RE.search(q)
    k = _KCB_RE.search(q)
    return {"grade": int(g.group(1)) if g else None,
            "nice": int(n.group(1)) if n else None,
            "kcb": int(k.group(1)) if k else None}


# ---------- 조립 헬퍼 ----------

def _fact(label: str, etype: str, props: dict, source: str) -> dict:
    """UI '구조화 사실' 카드 호환 형태."""
    return {"label": label, "etype": etype,
            "properties": {k: v for k, v in props.items() if v not in (None, "")},
            "source_file": source, "rels": [], "score": 1.0}


def _target_customers(q: str, grade: int) -> list[str]:
    """질문에 고객유형 명시 시 그것만. 없으면 정책(SHOW_BOTH_CUSTOMERS)에 따라
    데이터가 있는 유형 모두 / 첫 유형만."""
    exp = [ct for ct in ("내국인", "외국인") if ct in q]
    if exp:
        return exp
    avail = available_customers(grade)
    return avail if R.SHOW_BOTH_CUSTOMERS else avail[:1]


def _rate_str(rows_sel: list[dict]) -> str:
    if len(rows_sel) == 1:
        return rows_sel[0]["gl_rate"]
    return ", ".join(R.TERM_ITEM.format(months=_int(r["term_min_months"]), rate=r["gl_rate"])
                     for r in rows_sel)


def _answer_rate(q: str) -> dict | None:
    m = _GRADE_RE.search(q)
    if not m or not any(k in q for k in ("금리", "네고", "이자율", "nego", "NEGO")):
        return None
    grade = int(m.group(1))
    tm = _TERM_RE.search(q)
    term_min = int(tm.group(1)) if tm else None
    customers = _target_customers(q, grade)
    if not customers:
        return None

    ql = q.lower()
    requested = [n for n in R.NEGO_NAMES if n.lower() in ql] if R.NEGO_FILTER_BY_QUERY else []

    blocks, facts, sources = [], [], set()
    for ct in customers:
        rates = lookup_rates(grade, ct)
        if not rates:
            continue
        # 개월 지정 시 그 이하 최대 구간 1건. 미지정 시 정책(LIST_TERMS)에 따라 전체 나열/최소 1건.
        if term_min is not None:
            elig = [r for r in rates if _int(r.get("term_min_months"), 0) <= term_min]
            rows_sel = [elig[-1]] if elig else [rates[0]]
        else:
            rows_sel = rates if R.LIST_TERMS else [rates[0]]
        rate_str = _rate_str(rows_sel)

        negos = lookup_nego(grade, ct)
        if requested:
            negos = [n for n in negos if (n.get("nego_type") or "") in requested]

        line = R.RATE_BLOCK.format(ct=ct, grade=grade, rate_str=rate_str)
        if negos:
            nstr = ", ".join(R.NEGO_ITEM.format(type=n["nego_type"], rate=n["rate"]) for n in negos)
            line += R.RATE_NEGO_SUFFIX.format(nstr=nstr)
        blocks.append(line)

        for r in rows_sel + negos:
            if r.get("source"):
                sources.add(r["source"])
        facts.append(_fact(f"금리등급 {grade}등급 ({ct})", "RateGrade",
                           {"customer_type": ct, "기준금리": rate_str,
                            "네고": ", ".join(R.NEGO_ITEM.format(type=n["nego_type"], rate=n["rate"])
                                            for n in negos) or None},
                           rows_sel[0].get("source", "")))

    if not blocks:
        return None
    return {"answer": "\n".join(blocks), "sources": sorted(sources),
            "facts": facts, "matched": "rate_grade"}


def _promo_criteria(row: dict) -> list[tuple]:
    """프로모션 행 → [(표시문구, kind, 임계값)]. 임계값 컬럼에서 생성."""
    out = []
    g = _int(row.get("grade_req"))
    if g is not None:
        out.append((R.PROMO_CRIT_GRADE.format(v=g), "grade", g))
    n = _int(row.get("nice_min"))
    if n is not None:
        out.append((R.PROMO_CRIT_NICE.format(v=n), "nice", n))
    k = _int(row.get("kcb_min"))
    if k is not None:
        out.append((R.PROMO_CRIT_KCB.format(v=k), "kcb", k))
    return out


def _valstr(kind: str, v: int) -> str:
    return f"{v}등급" if kind == "grade" else f"{v}점"


def _eval_promo(row: dict, uv: dict):
    """사용자 값 uv를 프로모션 기준과 대조. (기준리스트, 통과, 미달, 미확인) 반환."""
    crit = _promo_criteria(row)
    passes, fails, unknowns = [], [], []
    for text, kind, thr in crit:
        val = uv.get(kind)
        if val is None:
            unknowns.append((text, kind, thr))
            continue
        ok = (val <= thr) if kind == "grade" else (val >= thr)   # 등급은 숫자가 낮을수록 상위
        (passes if ok else fails).append((text, kind, thr, val))
    return crit, passes, fails, unknowns


def _answer_promotion(q: str) -> dict | None:
    if "프로모션" not in q:
        return None
    rows = lookup_promotion()
    if not rows:
        return None

    uv = _user_values(q)
    has_user_val = any(v is not None for v in uv.values())

    # (A) 사용자가 값을 제시 → 가능/불가 판정
    if has_user_val:
        row = rows[0]  # 단일 프로모션 가정(여러 개면 첫 행 기준; 확장은 CSV로)
        crit, passes, fails, unknowns = _eval_promo(row, uv)
        crit_str = ", ".join(t for t, _, _ in crit)
        rate = row.get("gl_rate", "")
        exc = row.get("exclude", "")
        tail = R.PROMO_EXCLUDE_TAIL.format(exclude=exc) if exc else ""
        base = R.PROMO_BASE.format(crit=crit_str, rate=rate, tail=tail)

        # 정책: 하나라도 미달이면 불가(PROMO_REQUIRE_ALL)
        if fails or (not R.PROMO_REQUIRE_ALL and False):
            fs = ", ".join(R.PROMO_FAIL_ITEM.format(
                label=R.KIND_LABEL[k], valstr=_valstr(k, v), thrstr=_valstr(k, thr))
                for _, k, thr, v in fails)
            ans = R.PROMO_FAIL.format(base=base, fails=fs)
            verdict = "불가"
        elif unknowns:
            us = ", ".join(t for t, _, _ in unknowns)
            ps = ", ".join(f"{R.KIND_LABEL[k]} {_valstr(k, v)}" for _, k, _, v in passes)
            ans = R.PROMO_UNKNOWN.format(passes=ps, unknowns=us, base=base)
            verdict = "확인필요"
        else:
            ans = R.PROMO_PASS.format(base=base)
            verdict = "가능"

        facts = [_fact("프로모션 기준", "RateGrade",
                       {"기준": crit_str, "gl_rate": rate, "제외": exc, "판정": verdict},
                       row.get("source", ""))]
        srcs = [row["source"]] if row.get("source") else []
        return {"answer": ans, "sources": srcs, "facts": facts, "matched": "promotion_eval"}

    # (B) 값 없이 기준만 질문 → 기준 안내
    lines, facts, sources = [], [], set()
    for r in rows:
        crit = _promo_criteria(r)
        crit_str = ", ".join(t for t, _, _ in crit)
        rate, exc = r.get("gl_rate", ""), r.get("exclude", "")
        tail = R.PROMO_EXCLUDE_TAIL_SP.format(exclude=exc) if exc else ""
        lines.append(R.PROMO_LIST_ITEM.format(crit=crit_str, rate=rate, tail=tail))
        facts.append(_fact("프로모션 기준", "RateGrade",
                           {"기준": crit_str, "gl_rate": rate, "제외": exc}, r.get("source", "")))
        if r.get("source"):
            sources.add(r["source"])
    ans = (R.PROMO_LIST_HEADER + "\n- ".join(lines)) if len(lines) > 1 else lines[0] + "."
    return {"answer": ans, "sources": sorted(sources), "facts": facts, "matched": "promotion"}


def answer_numeric(question: str) -> dict | None:
    """수치형 결정적 답. 순서: 프로모션 → 금리등급/네고. 없으면 None."""
    q = question or ""
    return _answer_promotion(q) or _answer_rate(q)
