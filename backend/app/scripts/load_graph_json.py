"""
기존 graph_output/graph.json (networkx node-link 포맷)을 Neo4j에 적재.

사용:
    cd backend && python -m app.scripts.load_graph_json ../graph_output/graph.json

노드 스키마: {id, label, norm_label, file_type, source_file, community, ...}
엣지 스키마: {source, target, relation, confidence, confidence_score, source_file, weight}
모든 엔티티는 :Entity 라벨 + relation은 동적 타입(:REL)으로 적재한다.
"""
import json
import sys
from pathlib import Path

from app.neo4j_client import client


def load(graph_json_path: str) -> None:
    data = json.loads(Path(graph_json_path).read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    links = data.get("links", [])

    # 초기화 (PoC: 매번 새로 적재)
    client.run("MATCH (n) DETACH DELETE n")

    # 제약/인덱스
    client.run("CREATE CONSTRAINT entity_id IF NOT EXISTS "
               "FOR (e:Entity) REQUIRE e.id IS UNIQUE")

    # 노드 적재
    client.run(
        """
        UNWIND $nodes AS n
        MERGE (e:Entity {id: n.id})
        SET e.label = n.label,
            e.norm_label = n.norm_label,
            e.file_type = n.file_type,
            e.source_file = n.source_file,
            e.community = n.community
        """,
        {"nodes": nodes},
    )

    # 엣지 적재 (relation 을 속성으로; 타입은 공통 :REL)
    client.run(
        """
        UNWIND $links AS l
        MATCH (s:Entity {id: l.source})
        MATCH (t:Entity {id: l.target})
        MERGE (s)-[r:REL {relation: l.relation}]->(t)
        SET r.confidence = l.confidence,
            r.confidence_score = l.confidence_score,
            r.source_file = l.source_file,
            r.weight = l.weight
        """,
        {"links": links},
    )

    print(f"적재 완료: nodes={len(nodes)}, links={len(links)}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../graph_output/graph.json"
    load(path)
