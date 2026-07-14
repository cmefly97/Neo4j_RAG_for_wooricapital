"""환경설정 로드 (.env). 실제 .env 키 구조에 정렬."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # backend/ 또는 프로젝트 루트(../) 어디에 .env가 있어도 인식
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # ===== Neo4j =====
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme-please"

    # ===== LLM: Anthropic (Claude) =====
    anthropic_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com/v1/messages"
    anthropic_extract_model: str = "claude-sonnet-4-6"
    anthropic_answer_model: str = "claude-sonnet-4-6"

    # ===== LLM: HyperCLOVA X (사내 게이트웨이, OpenAI 호환) =====
    hcx_provider: str = "hyperclova"
    hcx_api_key: str = ""
    hcx_base_url: str = ""                 # 예: https://.../v1/chat/completions
    hcx_extract_model: str = "HyperCLOVAX-SEED-32B-Think-Text"
    hcx_answer_model: str = "HyperCLOVAX-SEED-32B-Think-Text"

    # ===== LLM: Qwen (사내 게이트웨이, OpenAI 호환) =====
    # base_url/api_key 미설정 시 HCX 게이트웨이/키를 재사용한다.
    qwen_api_key: str = ""
    qwen_base_url: str = ""
    qwen_model: str = "Qwen3.6-35B-A3B"

    # ===== LLM: HCX-30B-Text (사내 게이트웨이, OpenAI 호환, thinking 지원) =====
    hcx30_api_key: str = ""
    hcx30_base_url: str = ""            # 예: http://223.130.140.68:11000/v1/chat/completions
    hcx30_model: str = "hcx-agent-05"

    # ===== Embeddings (사내 게이트웨이, OpenAI 호환 /v1/embeddings) =====
    # base_url/api_key 미설정 시 HCX 게이트웨이/키를 재사용한다.
    embed_api_key: str = ""
    embed_base_url: str = ""            # 예: https://namc-aigw.io.naver.com/v1
    embed_model: str = "bge-m3"
    embed_dim: int = 1024              # bge-m3 = 1024차원

    # ===== App =====
    backend_port: int = 8000
    source_dir: str = "./source"
    graph_json: str = "./graph_output/graph.json"


    @property
    def embed_base(self) -> str:
        """임베딩 base_url. 미설정 시 HCX 게이트웨이 재사용(.../v1 로 정규화)."""
        url = self.embed_base_url or self.hcx_base_url
        return url.split("/chat/completions")[0].rstrip("/") if url else url

    @property
    def embed_key(self) -> str:
        return self.embed_api_key or self.hcx_api_key

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
