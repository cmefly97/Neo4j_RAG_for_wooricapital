"""
검색 로직 상세 테스트 — 실제 정답 텍스트를 본뜬 가짜 청크로 5개 샘플질문 검증.
가짜 Neo4j가 Neo4j의 CONTAINS-any/점수정렬을 파이썬으로 재현 → 네트워크/DB 불필요.
"""
import pytest
import app.search.cypher_qa as qa

# 실제 source 문서 발췌를 본뜬 청크 (정답 포함)
FAKE_CHUNKS = [
    {"text": "취급 가능 개월수: 론/할부 구입대출 12~72개월 적용", "source": "9_중고승용 상품운영기준.pdf"},
    {"text": "금리등급 2등급 21.0% G/L금리. NICE 1등급이므로 1% 네고. "
             "거점장 네고 11.0%, 증빙 네고 15.0%, HJ 네고 18.0%", "source": "9_중고승용 상품운영기준.pdf"},
    {"text": "듀얼상품(Dual Offer). Dual_C 판정 내국인 7등급 외국인 7등급, "
             "Dual_O 판정 내국인 7등급 외국인 7등급 까지", "source": "9_중고승용 상품운영기준.pdf"},
    {"text": "엔카 슬라이딩: 국산차/수입차 & 19년식 이내 & 주행거리 연평균 500만km 이하, "
             "카히스토리 사고 33백만원 이내 & 특수사고(전손/침수/도난/부활) 없는 차량", "source": "9_중고승용 상품운영기준.pdf"},
    {"text": "신용구제 상품: 신용회복/개인회생 고객. R판정인 경우 '필터링 취급 불가' 대상", "source": "9_중고승용 상품운영기준.pdf"},
    {"text": "중고리스 잔가율표 및 IRR 산정 기준 (무관한 청크)", "source": "8_중고리스.pdf"},
]


class FakeClient:
    """Neo4j 동작 재현 (CONTAINS-any, score, ORDER BY, LIMIT)."""
    def __init__(self, chunks=FAKE_CHUNKS):
        self.chunks = chunks
    def run_readonly(self, cypher, params=None):
        params = params or {}
        if "count(c)" in cypher:
            return [{"n": len(self.chunks)}]
        if "MATCH (c:Chunk)" in cypher and "$kws" in cypher:
            kws = [k.lower() for k in params.get("kws", [])]
            scored = []
            for c in self.chunks:
                tl = c["text"].lower()
                score = sum(1 for kw in kws if kw in tl)
                if score > 0:
                    scored.append({"text": c["text"], "source": c["source"], "score": score})
            scored.sort(key=lambda r: r["score"], reverse=True)
            return scored[: params.get("limit", 6)]
        if "MATCH (e:Entity)" in cypher:
            return []
        return []


class FakeLLM:
    def invoke(self, prompt):
        class M:  # 답변은 컨텍스트를 그대로 반영(채점은 rows로)
            content = "답변(발췌 기반): " + prompt.split("[문서 발췌]")[-1][:200]
        return M()


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(qa, "client", FakeClient())
    monkeypatch.setattr(qa, "_is_available", lambda spec: True)
    monkeypatch.setattr(qa, "build_chat_model", lambda mid: FakeLLM())


# ── 키워드 추출 ──────────────────────────────────────────
def test_keywords_synonym_expansion():
    kws = qa._keywords("듀얼상품 금리등급 몇등급까지 취급 가능해?")
    low = [k.lower() for k in kws]
    assert "dual" in low          # 듀얼→Dual 확장
    assert "금리등급" in kws
    assert "가능해" not in kws      # 불용어 제거


# ── 5개 샘플질문이 올바른 청크를 최상위로 찾는지 ──────────
SAMPLES = [
    ("론/할부 상품 취급 가능 개월수가 어떻게돼?", "12~72개월"),
    ("론/할부 나이스 885점, 금리등급 2등급일 때 적용 될 수 있는 최저 금리 알려줘", "21.0%"),
    ("듀얼상품 금리등급 몇등급까지 취급 가능해?", "Dual_C"),
    ("엔카 슬라이딩 가능해?", "슬라이딩"),
    ("신용구제 상품에서 신용회복, 개인회생 고객인데 판정값이 R 판정이야", "필터링 취급 불가"),
]

@pytest.mark.parametrize("q,expected", SAMPLES, ids=[s[0][:12] for s in SAMPLES])
def test_sample_questions_retrieve_correct_chunk(patched, q, expected):
    r = qa.search(q, "hyperclova")
    assert r["rows"], f"검색 결과 없음: {q}"
    assert expected in r["rows"][0]["text"], (
        f"최상위 청크에 기대값 '{expected}' 없음. top={r['rows'][0]['text'][:80]}")
    assert expected in r["answer"]  # 답변이 해당 청크를 근거로 생성


# ── 청크 미적재 → 개념 폴백 ───────────────────────────────
def test_no_chunks_falls_back_to_entity(monkeypatch):
    class Empty(FakeClient):
        def __init__(self): super().__init__(chunks=[])
    monkeypatch.setattr(qa, "client", Empty())
    r = qa.search("듀얼상품?", "claude")
    assert "청크 미적재" in r["model_used"]


# ── LLM 미가용 → 발췌 원문 반환 ──────────────────────────
def test_llm_unavailable_returns_excerpt(monkeypatch):
    monkeypatch.setattr(qa, "client", FakeClient())
    monkeypatch.setattr(qa, "_is_available", lambda spec: False)
    r = qa.search("엔카 슬라이딩 가능해?", "claude")
    assert "슬라이딩" in r["answer"] and r["rows"]


# ── LLM 오류 → 발췌로 강등(예외 전파 안 함) ──────────────
def test_llm_error_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(qa, "client", FakeClient())
    monkeypatch.setattr(qa, "_is_available", lambda spec: True)
    def boom(mid): raise RuntimeError("LLM down")
    monkeypatch.setattr(qa, "build_chat_model", boom)
    r = qa.search("엔카 슬라이딩 가능해?", "claude")
    assert "LLM 오류" in r["model_used"] and r["rows"]


# ── 매칭 없음 → 안내 메시지 ──────────────────────────────
def test_no_match_message(patched):
    r = qa.search("아무관련없는질문xyz", "hyperclova")
    assert r["rows"] == [] and "찾지 못했" in r["answer"]


# ── Neo4j 미연결 → 친절 안내(예외 전파 안 함) ────────────
def test_neo4j_down_returns_friendly(monkeypatch):
    from neo4j.exceptions import ServiceUnavailable
    class Down:
        def run_readonly(self, c, p=None):
            raise ServiceUnavailable("Couldn't connect to localhost:7687 ... refused")
    monkeypatch.setattr(qa, "client", Down())
    r = qa.search("엔카 슬라이딩 가능해?", "claude")
    assert r["rows"] == [] and "Neo4j" in r["answer"]
    assert "미연결" in r["model_used"]
