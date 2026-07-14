"""
검색 (GraphRAG-lite): 결정적 키워드 청크검색 → LLM 답변 1회.

이전 방식(LLM이 Cypher 생성)은 키워드가 brittle하고(예: '취급개월수' vs '취급 가능 개월수')
thinking 모델로 2회 호출해 매우 느렸다(>10분). 그래서:
  1) 질문에서 핵심 키워드 추출(+한/영 동의어)
  2) Neo4j에서 Chunk.text를 키워드 부분일치로 검색·점수정렬 (결정적, 1쿼리)
  3) 상위 청크를 근거로 LLM이 한국어 답변 1회 생성 (출처 포함)
반환: {"answer", "cypher", "rows", "model_used"}
"""
import re

from app.neo4j_client import client
from app.llm import build_chat_model, get_model_spec
from app.llm.registry import _is_available
from app.logging_setup import log_action
from app.search.router import route_intent
from app.search import tables
from app.search import answer_rules as R
from app.search.prompts import (ANSWER_PROMPTS, ANSWER_STYLES, DEFAULT_ANSWER_MODE,
                                answer_prompt as _answer_prompt)

# 질문에서 제거할 비핵심어
STOPWORDS = {
    "상품", "알려줘", "알려", "어떻게", "어떻게돼", "어떻게되", "가능", "가능해", "가능한",
    "경우", "인데", "이야", "해줘", "무엇", "그리고", "또는", "에서", "에는", "관련",
    "적용", "있는", "있어", "되는", "되나", "되니", "한지", "인지", "대해", "대한",
}
# 도메인 한/영 동의어 (토큰에 base가 포함되면 확장)
SYNONYMS = {
    "듀얼": ["듀얼", "Dual", "dual"],
    "개월수": ["개월"],
    "개월": ["개월"],
    "엔카": ["엔카", "encar"],
    "슬라이딩": ["슬라이딩", "sliding"],
    "금리등급": ["금리등급", "등급"],
    "신용구제": ["신용구제"],
    "개인회생": ["개인회생"],
    "신용회복": ["신용회복"],
}

CHUNK_SEARCH = (
    "MATCH (c:Chunk) "
    "WHERE any(kw IN $kws WHERE toLower(c.text) CONTAINS toLower(kw)) "
    "WITH c, size([kw IN $kws WHERE toLower(c.text) CONTAINS toLower(kw)]) AS score "
    "RETURN c.text AS text, c.source_file AS source, score "
    "ORDER BY score DESC LIMIT $limit"
)

# 답변 스타일/프롬프트 룰은 app/search/prompts.py 로 분리(위에서 import).

# 구조화 엔티티 속성 중 답변에 불필요한 메타키
_META_KEYS = {"id", "origin", "label", "etype", "source_file", "norm_label",
              "community", "file_type"}


def _keywords(question: str) -> list[str]:
    toks = re.findall(r"[가-힣A-Za-z0-9]+", question)
    out = []
    for t in toks:
        if len(t) < 2 or t in STOPWORDS:
            continue
        out.append(t)
        for base, syns in SYNONYMS.items():
            if base in t:
                out.extend(syns)
    # 중복 제거(순서 유지)
    seen, uniq = set(), []
    for k in out:
        if k.lower() not in seen:
            seen.add(k.lower()); uniq.append(k)
    return uniq


def _chunk_count() -> int:
    r = client.run_readonly("MATCH (c:Chunk) RETURN count(c) AS n")
    return r[0]["n"] if r else 0


def _is_conn_error(e: Exception) -> bool:
    blob = (type(e).__name__ + " " + str(e)).lower()
    return any(k in blob for k in
               ("serviceunavailable", "connect", "refused", "resolve", "routing"))


def _entity_fallback(question: str) -> dict:
    """Chunk가 없을 때(개념 그래프만 적재) 라벨 부분일치 폴백."""
    kws = _keywords(question)
    cypher = ("MATCH (e:Entity) WHERE any(kw IN $kws WHERE toLower(e.label) CONTAINS toLower(kw)) "
              "OPTIONAL MATCH (e)-[r:REL]-(n:Entity) "
              "RETURN e.label AS entity, r.relation AS relation, n.label AS neighbor, "
              "e.source_file AS source LIMIT 25")
    rows = client.run_readonly(cypher, {"kws": kws})
    return {"answer": f"개념 그래프에서 {len(rows)}건을 찾았습니다. (문서 청크 미적재 — "
                      f"`ingest_source` 실행 시 더 정확한 답변 가능)",
            "cypher": cypher, "rows": rows}


# 구조화 사실 최소 점수(주변적 매칭 컷). label/prop 1건=2, 이웃 1건=1, 의도 일치=+5
_FACT_MIN_SCORE = 3

# 질문 의도 → 우선할 etype (개선 ②: 의도별 우선순위)
_INTENT_RULES = [
    (("개월", "기간", "취급"), ["Product", "RateGrade"]),
    (("금리", "등급", "네고", "nego"), ["RateGrade", "Nego"]),
    (("판정", "취급불가", "필터링", "취급 불가"), ["Decision"]),
    (("엔카", "슬라이딩", "연식", "주행", "카히스토리", "차량", "잔가"), ["VehicleCondition"]),
    (("듀얼", "dual"), ["Product", "RateGrade"]),
]


def _intent_etypes(question: str) -> list[str]:
    q = (question or "").lower()
    out: list[str] = []
    for terms, etypes in _INTENT_RULES:
        if any(t.lower() in q for t in terms):
            out += etypes
    return list(dict.fromkeys(out))   # 중복 제거(순서 유지)


def _structured_facts(question: str, kws: list[str]) -> list[dict]:
    """구조화 그래프(origin='structured')에서 질문과 관련된 사실을 점수순으로.
    개선 ①: 라벨뿐 아니라 **값 속성·이웃(관계 대상) 라벨**까지 매칭.
    개선 ②: 질문 의도에 맞는 **etype에 가산점**. 미적재/오류 시 []."""
    if not kws:
        return []
    cypher = (
        "MATCH (e:Entity) WHERE e.origin='structured' "
        "OPTIONAL MATCH (e)-[r:REL]->(n:Entity) "
        "WITH e, collect(DISTINCT {rel:r.relation, target:n.label}) AS rels0 "
        "WITH e, [x IN rels0 WHERE x.target IS NOT NULL] AS rels, "
        "  size([kw IN $kws WHERE toLower(e.label) CONTAINS toLower(kw)]) AS label_hits, "
        "  size([k IN keys(e) WHERE NOT k IN $meta AND "
        "       any(kw IN $kws WHERE toLower(toString(e[k])) CONTAINS toLower(kw))]) AS prop_hits, "
        "  size([x IN [y IN rels0 WHERE y.target IS NOT NULL] WHERE "
        "       any(kw IN $kws WHERE toLower(x.target) CONTAINS toLower(kw))]) AS nbr_hits "
        "WITH e, rels, label_hits, prop_hits, nbr_hits, "
        "  (label_hits*2 + prop_hits*2 + nbr_hits + "
        "   CASE WHEN e.etype IN $intent THEN 5 ELSE 0 END) AS score "
        "WHERE score >= $minscore "                       # 개선 ①: 저점수(주변적) 제외
        "RETURN e.label AS label, e.etype AS etype, properties(e) AS props, "
        "  e.source_file AS source, rels[..5] AS rels, score "
        "ORDER BY score DESC LIMIT 8")
    try:
        return client.run_readonly(
            cypher, {"kws": kws, "meta": list(_META_KEYS),
                     "intent": _intent_etypes(question), "minscore": _FACT_MIN_SCORE})
    except Exception:  # noqa: BLE001
        return []


def _facts_text(facts: list[dict]) -> str:
    lines = []
    for f in facts:
        props = {k: v for k, v in (f.get("props") or {}).items() if k not in _META_KEYS}
        kv = ", ".join(f"{k}={v}" for k, v in props.items())
        line = f"- [{f.get('etype')}] {f.get('label')}" + (f" ({kv})" if kv else "")
        rels = [x for x in (f.get("rels") or []) if x.get("target")]
        if rels:
            line += " / " + ", ".join(f"{x['rel']}→{x['target']}" for x in rels)
        lines.append(line)
    return "\n".join(lines)


# HCX-30B 등 사내 모델은 입력이 일정 길이를 넘으면 빈 응답 → 총량만 캡(청크당은 원문 유지)
_MAX_CTX_CHARS = 5500     # 문서 발췌 부분 총량 상한(8180 실패보다 낮게 → 답변 풍부 + 안전)
_MAX_CHUNK_CHARS = 1500   # 청크당 상한(원복 — 답변이 짧아지지 않도록)


def _build_context(rows: list[dict], facts: list[dict] | None = None) -> str:
    # 개선 ②: 문서 발췌(1차 근거)를 앞에, 구조화 사실은 뒤에 '보조 참고'로 배치
    # + 입력 한도 방어: 청크당 길이 축소 + 총량이 예산을 넘으면 상위 청크까지만 포함
    chunk_parts, used = [], 0
    for r in rows:
        t = (r.get("text") or "")[:_MAX_CHUNK_CHARS]
        seg = f"[{r.get('source')}] {t}"
        if chunk_parts and used + len(seg) > _MAX_CTX_CHARS:
            break                     # 최소 1개는 포함, 예산 초과 시 중단
        chunk_parts.append(seg); used += len(seg)
    parts = ["[문서 발췌]\n" + "\n\n---\n".join(chunk_parts)]
    if facts:
        parts.append("[참고: 구조화 사실 — 보조, 발췌와 상충 시 발췌 우선]\n" + _facts_text(facts))
    return "\n\n".join(parts)


def _gen_answer(question: str, context: str, spec,
                answer_mode: str | None = None) -> tuple[str, str, str, str | None]:
    """LLM 답변 1회 생성(answer_mode: standard|concise|detailed). 반환: (answer, model_used, status, error)."""
    prompt = _answer_prompt(answer_mode)
    # 런타임 로그: 최종 LLM 호출(융합 컨텍스트 → 답변)
    log_action("LLM_CALL", model=spec.label, mode=(answer_mode or DEFAULT_ANSWER_MODE),
               ctx_chars=len(context))
    if _is_available(spec):
        try:
            llm = build_chat_model(spec.id)
            answer = llm.invoke(
                prompt.format(question=question, context=context)).content
            log_action("LLM_ANSWER", model=spec.label, chars=len(answer or ""),
                       preview=(answer or "")[:200])
            # 빈 응답(thinking 모델이 큰 컨텍스트에서 최종 답 미출력) → thinking 끄고 1회 재시도
            if not (answer or "").strip() and spec.supports_thinking:
                log_action("LLM_RETRY_NOTHINK", level="WARNING", model=spec.label,
                           ctx_chars=len(context))
                llm2 = build_chat_model(spec.id, disable_extra_body=True)
                answer = llm2.invoke(
                    prompt.format(question=question, context=context)).content
                log_action("LLM_ANSWER_RETRY", model=spec.label,
                           chars=len(answer or ""), preview=(answer or "")[:200])
            if not (answer or "").strip():          # 그래도 비면 발췌 폴백
                log_action("LLM_EMPTY", level="WARNING", model=spec.label,
                           ctx_chars=len(context))
                return (context[:1800], f"{spec.label} (빈 응답)", "llm_error",
                        "모델이 빈 응답을 반환했습니다. 발췌를 표시합니다.")
            return answer, spec.label, "ok", None
        except Exception as e:  # noqa: BLE001
            log_action("LLM_ERROR", level="ERROR", model=spec.label,
                       error=f"{type(e).__name__}: {e}")
            return (context[:1800], f"{spec.label} (LLM 오류)", "llm_error",
                    f"{type(e).__name__}: {e}")
    log_action("LLM_SKIP", model=spec.label, reason="no_key")
    return (context[:1800], f"{spec.label} (키 미설정)", "no_key",
            "선택한 모델의 API 키가 설정되지 않았습니다(.env 확인).")


def _retrieve(question: str, kws: list[str]) -> tuple[list[dict], str, dict]:
    """Hybrid(벡터+풀텍스트) 우선, 실패/미비 시 키워드 청크검색 폴백.
    반환: (rows, retrieval_요약, retrieval_detail)."""
    try:
        from app.search.hybrid import retrieve, is_ready
        if is_ready():
            rows, detail = retrieve(question, k=8)
            if rows:
                return rows, "HYBRID(vector+fulltext, RRF)", detail
    except Exception:  # noqa: BLE001  # 인덱스/임베딩 문제 시 폴백
        pass
    rows = client.run_readonly(CHUNK_SEARCH, {"kws": kws, "limit": 6})
    detail = {"mode": "keyword", "steps": ["키워드 부분일치(CONTAINS) + 매칭 키워드 수로 점수화"],
              "cypher": CHUNK_SEARCH, "keywords": kws}
    return rows, CHUNK_SEARCH, detail


def search(question: str, model_id: str | None = None,
           answer_mode: str | None = None) -> dict:
    spec = get_model_spec(model_id)
    kws = _keywords(question)

    # 0) 질의 라우팅 — 의도 3분류(numeric/mixed/descriptive). 로깅·경로 분기용.
    route = route_intent(question)
    log_action("ROUTE", route=route["route"], has_num=route["has_num"],
               has_rule=route["has_rule"], num_hits=",".join(route["num_hits"]) or "-",
               rule_hits=",".join(route["rule_hits"]) or "-")

    # 0-1) 결정적 테이블 short-circuit — 수치형(금리등급/네고/프로모션)은 CSV에서
    #      값을 뽑아 템플릿으로 답한다(LLM/Neo4j 무개입 → 빈응답·환각 제거).
    det = tables.answer_numeric(question)
    if det:
        answer = det["answer"]
        if R.SHOW_SOURCES and det["sources"]:
            answer += "\n\n출처: " + ", ".join(f"[{s}]" for s in det["sources"])
        log_action("ANSWER_TABLE", route=route["route"], matched=det["matched"],
                   chars=len(det["answer"]), sources=",".join(det["sources"]) or "-")
        steps = [f"라우팅: {route['route']} (수치 힌트 우선)",
                 f"결정적 테이블 조회: {det['matched']} (LLM 미호출)",
                 "규정 값 → 템플릿으로 답변 조립"]
        return {"answer": answer, "cypher": "", "rows": [], "facts": det["facts"],
                "model_used": f"{spec.label} (테이블 결정적)", "keywords": kws,
                "route": route["route"], "status": "ok_table",
                "retrieval_detail": {"mode": "table", "steps": steps}}

    # Neo4j 연결 가드 — 미연결 시 친절 안내(raw 500 방지)
    try:
        chunk_n = _chunk_count()
    except Exception as e:  # noqa: BLE001
        if _is_conn_error(e):
            return {"answer": "Neo4j(리모트)에 연결할 수 없습니다. 연결을 확인하세요: "
                              "`python -m app.scripts.check_neo4j` (방화벽/VPN/.env URI 점검).",
                    "cypher": "", "rows": [], "status": "no_db",
                    "error": f"{type(e).__name__}: {e}",
                    "model_used": f"{spec.label} (Neo4j 미연결)"}
        raise

    # 청크가 없으면 개념 그래프 폴백 / 안내
    if chunk_n == 0:
        out = _entity_fallback(question)
        out["model_used"] = f"{spec.label} (청크 미적재)"
        out["status"] = "no_chunks"
        return out

    # 1) 검색: Hybrid(벡터+풀텍스트) 우선, 미비 시 키워드 청크검색 폴백
    rows, retrieval, retrieval_detail = _retrieve(question, kws)

    if not rows:
        return {"answer": "관련 문서 내용을 찾지 못했습니다. 질문을 바꿔보세요.",
                "cypher": retrieval, "retrieval_detail": retrieval_detail, "rows": [],
                "model_used": spec.label, "keywords": kws, "status": "no_results"}

    # 2) 구조화 사실(있으면) + 청크로 컨텍스트 구성 → LLM 답변 1회
    facts = _structured_facts(question, kws)
    context = _build_context(rows, facts)
    answer, model_used, status, error = _gen_answer(question, context, spec, answer_mode)

    # 검색→답변 전 과정을 상세 단계에 덧붙임(UI '검색 과정'에 그대로 노출)
    detail = dict(retrieval_detail)
    base_steps = list(detail.get("steps", []))
    intent = _intent_etypes(question)
    fact_step = (f"구조화 사실 {len(facts)}건 조회 — 라벨·값속성·관계 매칭 + 점수순"
                 + (f" (의도 우선 etype: {', '.join(intent)})" if intent else "")
                 + " → [구조화 사실] 블록"
                 if facts else "구조화 사실 0건(매칭 없음) — 문서 발췌만 사용")
    detail["steps"] = base_steps + [
        fact_step,
        "컨텍스트 구성: [구조화 사실] + [문서 발췌](상위 청크) 순으로 결합",
        f"선택 모델({model_used})이 위 컨텍스트만 근거로 한국어 답변 1회 생성(출처 포함)",
    ]
    detail["facts_count"] = len(facts)

    return {"answer": answer, "cypher": retrieval, "retrieval_detail": detail,
            "rows": rows, "facts": facts, "model_used": model_used, "keywords": kws,
            "route": route["route"], "status": status, "error": error}


def search_compare(question: str, model_id: str | None = None,
                   answer_mode: str | None = None) -> dict:
    """벡터 전용 vs Hybrid 검색을 같은 질문으로 나란히 실행(데모용).
    반환: {question, status, vector:{...}, hybrid:{...}} 또는 안내 status."""
    spec = get_model_spec(model_id)

    try:
        chunk_n = _chunk_count()
    except Exception as e:  # noqa: BLE001
        if _is_conn_error(e):
            return {"question": question, "status": "no_db",
                    "error": f"{type(e).__name__}: {e}",
                    "answer": "Neo4j에 연결할 수 없습니다. `check_neo4j`로 점검하세요."}
        raise
    if chunk_n == 0:
        return {"question": question, "status": "no_chunks",
                "answer": "적재된 문서가 없습니다. ingest_source → setup_hybrid 실행 필요."}

    try:
        from app.search.hybrid import retrieve, vector_only_retrieve, is_ready
    except Exception:  # noqa: BLE001
        is_ready = lambda: False  # noqa: E731

    if not is_ready():
        return {"question": question, "status": "no_vector",
                "answer": "비교하려면 벡터 검색이 필요합니다. setup_hybrid(임베딩+벡터 인덱스)를 먼저 실행하세요."}

    # 구조화 사실은 검색 방식과 무관(그래프에서 조회) → 양쪽에 동일 적용.
    # 이렇게 하면 Hybrid 측은 기본 검색 search()와 동일 파이프라인 → 동일 결과.
    kws = _keywords(question)
    facts = _structured_facts(question, kws)

    def _side(rows: list[dict], detail: dict) -> dict:
        if not rows:
            return {"rows": [], "facts": facts, "retrieval_detail": detail,
                    "answer": "검색 결과가 없습니다.", "model_used": spec.label,
                    "status": "no_results", "error": None}
        ans, mu, st, err = _gen_answer(question, _build_context(rows, facts), spec, answer_mode)
        return {"rows": rows, "facts": facts, "retrieval_detail": detail, "answer": ans,
                "model_used": mu, "status": st, "error": err}

    v_rows, v_detail = vector_only_retrieve(question, k=8)
    h_rows, h_detail = retrieve(question, k=8)
    return {"question": question, "status": "ok",
            "vector": _side(v_rows, v_detail), "hybrid": _side(h_rows, h_detail)}
