"""환경설정 로드 (.env). 실제 .env 키 구조에 정렬.

모든 값은 **.env 에서만** 받아온다(하드코딩된 기본값 없음).
누락된 키가 있으면 `Settings()` 생성 시 ValidationError로 즉시 실패한다.
새 설정이 필요하면 .env 에 키를 추가하고 여기에 필드를 선언한다.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # backend/ 또는 프로젝트 루트(../) 어디에 .env가 있어도 인식
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # ===== Neo4j =====
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    # ===== LLM: HCX-30B-Text (기준 베이스 모델, OpenAI 호환, thinking 지원) =====
    # 다른 모델(Claude·HyperCLOVA X·Qwen)은 모델 관리 부담으로 제거됨(2026-07-20).
    hcx30_api_key: str
    hcx30_base_url: str
    hcx30_model: str

    # ===== Embeddings (bge-m3, OpenAI 호환 /v1/embeddings) =====
    embed_api_key: str
    embed_base_url: str
    embed_model: str
    embed_dim: int

    # ===== App =====
    backend_port: int
    source_dir: str
    graph_json: str


    @property
    def embed_base(self) -> str:
        """임베딩 base_url (.../v1 로 정규화)."""
        url = self.embed_base_url
        return url.split("/chat/completions")[0].rstrip("/") if url else url

    @property
    def embed_key(self) -> str:
        return self.embed_api_key

    @property
    def source_path(self) -> Path:
        """실행 위치(cwd)와 무관하게 source 폴더를 찾는다.
        .env의 SOURCE_DIR이 상대경로여도 프로젝트 루트 기준으로 보정."""
        p = Path(self.source_dir)
        if p.exists():
            return p
        root = Path(__file__).resolve().parents[2]  # backend/app/config.py → 프로젝트 루트
        for c in (root / "source", root / self.source_dir.lstrip("./")):
            if c.exists():
                return c
        return p


settings = Settings()
