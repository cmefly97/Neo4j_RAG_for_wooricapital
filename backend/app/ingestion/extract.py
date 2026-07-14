"""
청크 → 그래프 요소 변환.

(A) build_chunk_graph: 결정적(LLM 불필요). 문서/청크 노드 + 텍스트 보존.
    - (:Document {id,name,source_file})
    - (:Chunk {id,text,source_file,locator}) -[:PART_OF]-> (:Document)
    검색이 청크 텍스트(실제 값 포함)를 retrieve → 답변 가능.

(B) extract_entities_llm: 선택. 선택 LLM으로 (엔티티, 관계) 추출 → 개념 그래프 보강.
    사내망 PC에서 HyperCLOVA X로 실행.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path


def _doc_id(source_file: str) -> str:
    return "doc::" + hashlib.md5(source_file.encode()).hexdigest()[:10]


def build_chunk_graph(chunks: list[dict]) -> dict:
    """청크 리스트 → {nodes, edges} (결정적)."""
    nodes, edges, docs = [], [], {}
    for c in chunks:
        sf = c["source_file"]
        if sf not in docs:
            did = _doc_id(sf)
            docs[sf] = did
            nodes.append({"_label": "Document", "id": did,
                          "name": Path(sf).name, "source_file": sf})
        nodes.append({"_label": "Chunk", "id": c["chunk_id"], "text": c["text"],
                      "source_file": sf, "locator": c["locator"]})
        edges.append({"source": c["chunk_id"], "target": docs[sf], "type": "PART_OF"})
    return {"nodes": nodes, "edges": edges}


# ── (B) LLM 엔티티/관계 추출 (선택) ────────────────────────
_EXTRACT_PROMPT = """너는 지식그래프 추출기다. 아래 문서 조각에서 도메인 엔티티와 관계를 추출하라.
한국어 도메인 용어(론/할부/듀얼상품/잔가율/엔카 슬라이딩/금리등급 등)는 그대로 사용.
JSON만 출력. 형식:
{{"entities":[{{"name":"...","type":"Product|Criteria|Term|Concept|Organization"}}],
  "relations":[{{"source":"...","relation":"has_property|references|applies_to","target":"..."}}]}}

[문서 조각]
{chunk}
"""


def extract_entities_llm(chunks: list[dict], model_id: str | None = None) -> dict:
    """선택 LLM으로 엔티티/관계 추출. (네트워크/LLM 필요)"""
    from app.llm import build_chat_model
    llm = build_chat_model(model_id, role="extract")
    ents, rels = {}, []
    for c in chunks:
        try:
            out = llm.invoke(_EXTRACT_PROMPT.format(chunk=c["text"][:2000])).content
            m = re.search(r"\{.*\}", out, re.S)
            data = json.loads(m.group(0)) if m else {}
        except Exception:  # noqa: BLE001
            continue
        for e in data.get("entities", []):
            if e.get("name"):
                ents[e["name"]] = {"_label": "Entity", "id": e["name"],
                                   "label": e["name"], "etype": e.get("type", "Concept"),
                                   "source_file": c["source_file"]}
        for r in data.get("relations", []):
            if r.get("source") and r.get("target"):
                rels.append({"source": r["source"], "target": r["target"],
                             "relation": r.get("relation", "related_to"),
                             "source_file": c["source_file"]})
    return {"nodes": list(ents.values()), "edges": rels}
