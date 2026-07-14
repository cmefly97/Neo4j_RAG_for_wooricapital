"""
Hybrid 검색 — 벡터(bge-m3) + 풀텍스트(cjk)를 RRF로 융합.

- 벡터: 의미 유사(표현 달라도 뜻으로 검색)
- 풀텍스트: 한글 토큰/오타/정확 키워드
- 융합: Reciprocal Rank Fusion (순위 기반, 점수 스케일 차이에 강건)

인덱스 이름은 환경마다 다를 수 있어(예: chunkVec vs chunk_embedding_index)
**라벨/속성 기준으로 자동 탐지**한다. 읽기 전용(run_readonly) 경로.
"""
from __future__ import annotations
import re

from app.neo4j_client import client
from app.llm.embeddings import embedder
from app.logging_setup import log_action

# 한↔영 별칭/동의어 (풀텍스트 쿼리 확장)
SYNONYMS = {
    "듀얼": ["Dual", "Dual_C", "Dual_O"], "dual": ["듀얼"],
    "엔카": ["encar"], "슬라이딩": ["sliding"],
}
STOP = {"상품", "알려줘", "가능", "가능해", "경우", "어떻게", "무엇", "관련", "적용",
        "되나", "인지", "대해", "몇", "까지", "최저", "최대"}

_LUCENE_SPECIAL = r'([+\-!(){}\[\]^"~*?:\\/]|&&|\|\|)'

# 탐지된 인덱스 이름 캐시(성공 시에만 저장)
_cache: dict[str, str] = {}


def _find_index(itype: str, prop: str) -> str | None:
    """:Chunk(prop) 위의 ONLINE {itype} 인덱스 이름을 자동 탐지."""
    key = f"{itype}:{prop}"
    if key in _cache:
        return _cache[key]
    rows = client.run_readonly(
        "SHOW INDEXES YIELD name, type, state, labelsOrTypes, properties "
        "WHERE type=$t AND state='ONLINE' AND 'Chunk' IN labelsOrTypes "
        "AND $p IN properties RETURN name", {"t": itype, "p": prop})
    if not rows:
        return None
    # 우리 기본 이름 우선, 없으면 첫 번째
    names = [r["name"] for r in rows]
    name = next((n for n in names if n in ("chunkVec", "chunkText")), names[0])
    _cache[key] = name
    return name


def vector_index_name() -> str | None:
    return _find_index("VECTOR", "embedding")


def fulltext_index_name() -> str | None:
    return _find_index("FULLTEXT", "text")


def vec_cypher(name: str) -> str:
    return (f"CALL db.index.vector.queryNodes('{name}', $k, $qvec) YIELD node, score "
            "RETURN node.id AS id, node.text AS text, node.source_file AS source, "
            "node.locator AS locator, score")


def ft_cypher(name: str) -> str:
    return (f"CALL db.index.fulltext.queryNodes('{name}', $q) YIELD node, score "
            "RETURN node.id AS id, node.text AS text, node.source_file AS source, "
            "node.locator AS locator, score LIMIT $k")


def _lucene_query(question: str) -> str:
    toks = re.findall(r"[가-힣A-Za-z0-9.]+", question)
    terms: list[str] = []
    for t in toks:
        if len(t) < 2 or t in STOP:
            continue
        terms.append(t)
        for base, syns in SYNONYMS.items():
            if base in t:
                terms += syns
    seen, out = set(), []
    for t in terms:
        if t.lower() in seen:
            continue
        seen.add(t.lower())
        out.append(re.sub(_LUCENE_SPECIAL, r"\\\1", t))
    return " OR ".join(out) if out else (question or "").strip()


def _rrf(rank_lists: list[list[dict]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for lst in rank_lists:
        for rank, row in enumerate(lst):
            rid = row["id"]
            scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank + 1)
    return scores


def retrieve(question: str, k: int = 8, pool: int = 20, vec_guarantee: int = 3) -> tuple[list[dict], dict]:
    """벡터+풀텍스트 융합 상위 k개 + 검색 과정 상세(detail)를 함께 반환.

    - k=8 (개선 ①): 어휘 불일치 질의에서 정답 청크가 컷 밖으로 밀리지 않도록 여유 확대.
    - vec_guarantee (개선 ②): RRF 결과와 별개로 **벡터 상위 N개는 항상 포함**
      (의미상 강한 히트가 RRF 희석으로 유실되는 것을 방지).
    """
    vname, fname = vector_index_name(), fulltext_index_name()
    lq = _lucene_query(question)
    qvec = embedder.embed_one(question)
    vcy = vec_cypher(vname) if vname else None
    fcy = ft_cypher(fname) if fname else None
    vec_rows = client.run_readonly(vcy, {"k": pool, "qvec": qvec}) if vname else []
    ft_rows = client.run_readonly(fcy, {"q": lq, "k": pool}) if fname else []

    fused = _rrf([vec_rows, ft_rows])
    by_id = {r["id"]: r for r in (vec_rows + ft_rows)}
    ranked_ids = [rid for rid, _ in sorted(fused.items(), key=lambda kv: kv[1], reverse=True)]

    # 개선 ②: 벡터 상위 vec_guarantee개를 먼저 확정(순서 유지), 이후 RRF 순으로 채움
    order: list[str] = []
    for r in vec_rows[:vec_guarantee]:
        if r["id"] not in order:
            order.append(r["id"])
    for rid in ranked_ids:
        if rid not in order:
            order.append(rid)
    order = order[:k]

    out = []
    for rid in order:
        r = dict(by_id[rid]); r["score"] = round(fused.get(rid, 0.0), 5); out.append(r)

    # 런타임 로그: 벡터/풀텍스트 검색 + 융합 결과(최종 LLM에 들어갈 청크) 기록
    _loc = lambda rs: ", ".join(f"{x.get('source')}/{x.get('locator')}" for x in rs[:6])
    log_action("RETRIEVE", mode="hybrid", vector=len(vec_rows), fulltext=len(ft_rows),
               fused=len(out), lucene=lq,
               vec_top=_loc(vec_rows), ft_top=_loc(ft_rows))
    for i, r in enumerate(out, 1):
        log_action("CTX_CHUNK", i=i, src=f"{r.get('source')}/{r.get('locator')}",
                   score=r.get("score"), text=(r.get("text") or "")[:300])

    detail = {
        "mode": "hybrid",
        "steps": [
            f"1) 질문을 {embedder.model}로 임베딩 → {len(qvec)}차원 벡터로 변환",
            f"2) 벡터 인덱스({vname})에서 코사인 유사 상위 {pool}건 검색 — {len(vec_rows)}건",
            f"3) 풀텍스트 인덱스({fname}, cjk)에서 키워드 상위 {pool}건 검색 — {len(ft_rows)}건",
            f"4) RRF(k=60) 융합 + 벡터 상위 {vec_guarantee}건 보장 → 상위 {k}건 선정",
        ],
        "vector_index": vname, "fulltext_index": fname,
        "embed_model": embedder.model, "embed_dim": len(qvec),
        "lucene_query": lq, "vector_cypher": vcy, "fulltext_cypher": fcy,
        "fusion": f"RRF(k=60) + 벡터 상위 {vec_guarantee} 보장",
        "vector_hits": len(vec_rows), "fulltext_hits": len(ft_rows),
        "pool": pool, "top_k": k,
    }
    return out, detail


def hybrid_retrieve(question: str, k: int = 8, pool: int = 20) -> list[dict]:
    """하위호환 래퍼 — rows만 반환."""
    return retrieve(question, k, pool)[0]


def vector_only_retrieve(question: str, k: int = 6) -> tuple[list[dict], dict]:
    """벡터(임베딩)만 사용한 검색 — 비교 데모용. (rows, detail) 반환."""
    vname = vector_index_name()
    if not vname:
        return [], {"mode": "vector", "steps": ["벡터 인덱스가 없어 검색 불가"],
                    "vector_index": None}
    qvec = embedder.embed_one(question)
    vcy = vec_cypher(vname)
    rows = client.run_readonly(vcy, {"k": k, "qvec": qvec})
    out = []
    for r in rows[:k]:
        d = dict(r)
        if isinstance(d.get("score"), (int, float)):
            d["score"] = round(d["score"], 5)
        out.append(d)
    detail = {
        "mode": "vector",
        "steps": [
            f"질문을 {embedder.model}로 임베딩 → {len(qvec)}차원 벡터",
            f"벡터 인덱스({vname})에서 코사인 유사 상위 {k}건 검색 — {len(rows)}건",
        ],
        "vector_index": vname, "embed_model": embedder.model, "embed_dim": len(qvec),
        "vector_cypher": vcy, "vector_hits": len(rows), "top_k": k,
    }
    return out, detail


def is_ready() -> bool:
    """임베딩 사용 가능 + 벡터 인덱스 ONLINE(이름 무관) 존재."""
    if not embedder.is_available():
        return False
    try:
        return vector_index_name() is not None
    except Exception:  # noqa: BLE001
        return False
