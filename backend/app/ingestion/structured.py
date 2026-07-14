"""
구조화 추출 — 오토 운영기준 도메인 온톨로지 기반 LLM 엔티티/관계 추출.

청크 텍스트(깨진 표 포함)에서 '값을 가진' 엔티티를 뽑아 정밀 질의를 가능케 한다.
스키마 드리프트 방지를 위해 etype/relation 을 고정 화이트리스트로 제한한다.

산출: {"nodes":[{id,label,etype,source_file,props}], "edges":[{source,target,relation,source_file}]}
적재 시 기존 컨벤션과 동일하게 (:Entity {id,label,etype,...props})-[:REL {relation}]->(:Entity)
로 넣되 origin='structured' 로 태깅(개념 그래프와 구분/재적재 멱등).
"""
from __future__ import annotations
import json
import re
import hashlib

# 허용 엔티티 유형 (값 속성 예시는 프롬프트에서 안내)
ETYPES = [
    "Product",          # 상품: 중고승용 할부, Dual Offer, 신용구제 등
    "RateGrade",        # 금리등급: grade, gl_rate, max_months, customer(내국인/외국인)
    "Nego",             # 네고: nego_type(거점장/증빙/HJ/내국인/외국인), rate
    "Decision",         # 판정: code(R/B/...), result(취급가능/필터링 취급불가)
    "VehicleCondition", # 차량조건: 연식/주행거리/카히스토리/특수사고
    "HandlingRule",     # 취급기준/취급불가 등 일반 규칙
    "Term",             # 기타 도메인 용어(엔카 슬라이딩 등)
]
RELATIONS = ["HAS_RATE", "HAS_NEGO", "HAS_DECISION", "HAS_CONDITION",
             "HAS_RULE", "APPLIES_TO", "RELATED_TO"]

PROMPT = """너는 우리캐피탈 오토 운영기준 지식그래프 추출기다.
아래 '문서 조각'에서 도메인 엔티티와 관계를 JSON으로 추출하라. 한국어 용어(론/할부/듀얼/Dual/
엔카 슬라이딩/잔가율/금리등급/R판정 등)는 그대로 사용. 표가 깨져 있어도 행/열을 최대한 복원해
'값(수치·등급·판정결과)'을 attributes 에 담아라. 값이 불명확하면 추측하지 말고 생략.

엔티티 type 은 반드시 다음 중 하나: {etypes}
관계 relation 은 반드시 다음 중 하나: {relations}

attributes 예시:
- RateGrade: {{"grade":2,"gl_rate":"21.0%","max_months":72,"customer":"내국인"}}
- Nego: {{"nego_type":"거점장","rate":"11.0%"}}
- Decision: {{"code":"R","result":"필터링 취급 불가"}}
- VehicleCondition: {{"model_year":"19년식 이내","mileage":"연평균 500만km 이하","carhistory":"사고 33백만원 이내","special":"전손·침수·도난 없음"}}

JSON만 출력. 형식:
{{"entities":[{{"name":"중고승용 G/L 2등급","type":"RateGrade","attributes":{{...}}}}],
  "relations":[{{"source":"중고승용 할부","relation":"HAS_RATE","target":"중고승용 G/L 2등급"}}]}}

[문서 조각]
{chunk}
"""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def _eid(etype: str, name: str) -> str:
    h = hashlib.md5(f"{etype}|{_norm(name)}".encode("utf-8")).hexdigest()[:10]
    return f"{etype}::{h}"


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        return {}


def extract_from_text(text: str, source_file: str, llm) -> dict:
    """단일 청크 → {nodes, edges} (LLM 1회 호출). 호출측에서 예외 처리."""
    out = llm.invoke(PROMPT.format(
        etypes=", ".join(ETYPES), relations=", ".join(RELATIONS),
        chunk=text[:2500])).content
    data = _parse_json(out)

    nodes, name2id = {}, {}
    for e in data.get("entities", []):
        name, etype = e.get("name"), e.get("type")
        if not name or etype not in ETYPES:
            continue
        eid = _eid(etype, name)
        name2id[_norm(name)] = eid
        props = {k: v for k, v in (e.get("attributes") or {}).items()
                 if isinstance(v, (str, int, float)) and str(v).strip()}
        nodes[eid] = {"id": eid, "label": name, "etype": etype,
                      "source_file": source_file, "props": props}

    edges = []
    for r in data.get("relations", []):
        rel = r.get("relation")
        s, t = _norm(r.get("source", "")), _norm(r.get("target", ""))
        if rel not in RELATIONS or s not in name2id or t not in name2id:
            continue
        edges.append({"source": name2id[s], "target": name2id[t],
                      "relation": rel, "source_file": source_file})
    return {"nodes": list(nodes.values()), "edges": edges}
