"""
임베딩 클라이언트 — 사내 게이트웨이 bge-m3 (OpenAI 호환 /v1/embeddings).

stdlib(urllib)만 사용해 의존성 추가 없음. 배치 입력 지원.
설정: .env 의 EMBED_*(미설정 시 HCX 게이트웨이/키 재사용) → app.config.settings.

사용:
    from app.llm.embeddings import embedder
    vecs = embedder.embed(["질문1", "질문2"])   # -> [[...1024...], [...]]
    qv   = embedder.embed_one("엔카 슬라이딩 조건")
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error

from app.config import settings


class EmbeddingError(RuntimeError):
    pass


class Embedder:
    def __init__(self, base: str | None = None, key: str | None = None,
                 model: str | None = None, dim: int | None = None,
                 timeout: int = 60, batch_size: int = 32):
        self.base = (base or settings.embed_base or "").rstrip("/")
        self.key = key or settings.embed_key
        self.model = model or settings.embed_model
        self.dim = dim or settings.embed_dim
        self.timeout = timeout
        self.batch_size = batch_size

    def is_available(self) -> bool:
        return bool(self.base and self.key and self.model)

    @property
    def url(self) -> str:
        # base 는 .../v1 형태 → /embeddings 부착
        return f"{self.base}/embeddings"

    def _post(self, inputs: list[str]) -> list[list[float]]:
        body = json.dumps({"input": inputs, "model": self.model}).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:300]
            raise EmbeddingError(f"임베딩 HTTP {e.code}: {detail}") from e
        except Exception as e:  # noqa: BLE001
            raise EmbeddingError(f"임베딩 호출 실패: {type(e).__name__}: {e}") from e
        # OpenAI 호환 응답: {"data":[{"embedding":[...],"index":0}, ...]}
        items = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
        vecs = [it["embedding"] for it in items]
        if len(vecs) != len(inputs):
            raise EmbeddingError(f"임베딩 개수 불일치: 요청 {len(inputs)} / 응답 {len(vecs)}")
        return vecs

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.is_available():
            raise EmbeddingError(
                "임베딩 미설정: .env 의 EMBED_BASE_URL/EMBED_API_KEY(또는 HCX_*) 확인")
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            out += self._post(texts[i:i + self.batch_size])
        return out

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


embedder = Embedder()
