"""PoC 온톨로지(스키마) 정의 — 오토운영팀 도메인.
graph_output/GRAPH_REPORT.md 의 실제 추출 결과를 반영해 조정한다."""

NODE_TYPES = [
    "Document",       # 운영기준/심사기준 문서
    "Product",        # 론, 할부, 리스, 듀얼상품 등
    "Criteria",       # 심사기준(CSS), LTV, 한도CAP 등
    "Organization",   # 오토운영팀, 지점/본사
    "Concept",        # 신용평점, 잔가율 등
    "Term",           # 금리등급, 최저금리 등
]

# (source_type, relation, target_type)
RELATION_TYPES = [
    "has_class",
    "has_property",
    "references",
    "applies_to",
    "form",
]
