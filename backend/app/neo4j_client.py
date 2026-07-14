"""Neo4j 드라이버 래퍼 (읽기 전용 검색 가드 포함)."""
from neo4j import GraphDatabase
from .config import settings

_WRITE_KEYWORDS = ("CREATE", "MERGE", "DELETE", "SET", "REMOVE", "DROP", "DETACH")


class Neo4jClient:
    def __init__(self):
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self):
        self._driver.close()

    def run(self, cypher: str, params: dict | None = None):
        with self._driver.session() as session:
            return [r.data() for r in session.run(cypher, params or {})]

    def run_readonly(self, cypher: str, params: dict | None = None):
        """쓰기 키워드 차단 — 사용자 검색 경로 전용."""
        upper = cypher.upper()
        if any(kw in upper for kw in _WRITE_KEYWORDS):
            raise ValueError("읽기 전용 쿼리만 허용됩니다.")
        return self.run(cypher, params)


client = Neo4jClient()
