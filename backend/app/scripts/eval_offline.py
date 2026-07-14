"""오프라인 검색 검증(Neo4j/LLM 불필요) + 실행/에러 자동 로깅.

진단서(docs/04) 핵심 가설 확인:
  (1) 파싱이 정답값을 담은 청크를 만드는가
  (2) cypher_qa의 키워드 검색이 그 청크를 상위로 끌어올리는가
cypher_qa의 _keywords + CHUNK_SEARCH 스코어링을 재현해 top-k 청크와 정답 적중을 출력.

실행: cd backend && python -m app.scripts.eval_offline
로그: backend/logs/scripts_YYYY-MM-DD.log
"""
import re
import sys
from app.scripts._runlog import run, log_exc

# cypher_qa.py 와 동일한 키워드 로직(복제) ──────────────────────────────
STOPWORDS = {
    "상품", "알려줘", "알려", "어떻게", "어떻게돼", "어떻게되", "가능", "가능해", "가능한",
    "경우", "인데", "이야", "해줘", "무엇", "그리고", "또는", "에서", "에는", "관련",
    "적용", "있는", "있어", "되는", "되나", "되니", "한지", "인지", "대해", "대한",
}
SYNONYMS = {
    "듀얼": ["듀얼", "Dual", "dual"], "개월수": ["개월"], "개월": ["개월"],
    "엔카": ["엔카", "encar"], "슬라이딩": ["슬라이딩", "sliding"],
    "금리등급": ["금리등급", "등급"], "신용구제": ["신용구제"],
    "개인회생": ["개인회생"], "신용회복": ["신용회복"],
}


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
    seen, uniq = set(), []
    for k in out:
        if k.lower() not in seen:
            seen.add(k.lower()); uniq.append(k)
    return uniq
# ──────────────────────────────────────────────────────────────────────

CASES = [
    {"q": "론/할부 상품 취급 가능 개월수가 어떻게돼?", "expect": "12~72개월", "must": ["12", "72"]},
    {"q": "론/할부 나이스 885점, 금리등급 2등급일 때 적용 될 수 있는 최저 금리 알려줘",
     "expect": "2등급 21.0% G/L", "must": ["21.0"]},
    {"q": "듀얼상품 금리등급 몇등급까지 취급 가능해?", "expect": "Dual 7등급",
     "must": ["Dual", "7"]},  # 소스 문서는 한글 "듀얼"이 아닌 영문 "Dual" 사용
    {"q": "엔카 슬라이딩 가능해?", "expect": "엔카 슬라이딩 조건", "must": ["슬라이딩"]},
    {"q": "신용구제 상품에서 신용회복, 개인회생 고객인데 판정값이 R 판정이야",
     "expect": "R판정 = 필터링 취급 불가", "must": ["판정"]},
]
LIMIT = 6


def _search(chunks, kws, limit=LIMIT):
    scored = []
    for c in chunks:
        low = (c["text"] or "").lower()
        score = sum(1 for kw in kws if kw.lower() in low)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]


def _body(log):
    try:
        from app.scripts.ingest_source import collect_chunks
    except ModuleNotFoundError as e:
        log_exc(log, f"의존성 누락: {e.name}")
        log.error("→ 해결: cd backend && pip install -r requirements.txt. 누락=%s", e.name)
        return 1

    chunks = collect_chunks()
    log.info("총 청크 %d", len(chunks))
    passed = 0
    for i, case in enumerate(CASES, 1):
        kws = _keywords(case["q"])
        hits = _search(chunks, kws)
        blob = "\n".join(c["text"] for _, c in hits)
        found = [m for m in case["must"] if m.lower() in blob.lower()]
        ok = len(found) == len(case["must"])
        passed += ok
        log.info("[%d] Q=%s | 키워드=%s | 청크=%d | 정답토큰%s 적중%s => %s",
                 i, case["q"], kws, len(hits), case["must"], found,
                 "PASS" if ok else "MISS")
        for rank, (score, c) in enumerate(hits[:3], 1):
            snip = re.sub(r"\s+", " ", c["text"])[:140]
            log.info("    #%d(s=%d)[%s/%s] %s", rank, score,
                     c["source_file"], c["locator"], snip)
    log.info("검색 적중 %d/%d", passed, len(CASES))
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(run("eval_offline", _body))
