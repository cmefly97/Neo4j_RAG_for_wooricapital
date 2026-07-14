const BASE = "http://localhost:8000";

export type ModelInfo = {
  id: string;
  label: string;
  provider: string;
  available: boolean;
  default: boolean;
};

/** 공통 요청 래퍼: 콘솔 로깅 + 에러 시 메시지 throw */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`;
  const ts = new Date().toISOString();
  console.info(`[API ${ts}] → ${init?.method ?? "GET"} ${path}`);
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (e) {
    console.error(`[API ${ts}] ✗ 네트워크 실패 ${path}`, e);
    throw new Error(
      `백엔드에 연결할 수 없습니다 (${url}). 백엔드(uvicorn)가 실행 중인지 확인하세요.`
    );
  }
  const text = await res.text();
  let body: any = undefined;
  try { body = text ? JSON.parse(text) : undefined; } catch { body = text; }
  if (!res.ok) {
    const msg = body?.error ?? body?.detail ?? text ?? `HTTP ${res.status}`;
    console.error(`[API ${ts}] ✗ ${res.status} ${path}: ${msg}`);
    throw new Error(`서버 오류 (${res.status}): ${msg}`);
  }
  console.info(`[API ${ts}] ✓ ${res.status} ${path}`);
  return body as T;
}

export function listModels() {
  return request<{ models: ModelInfo[] }>("/models").then((r) => r.models);
}

export type RetrievalDetail = {
  mode: "hybrid" | "keyword" | "vector";
  steps?: string[];
  vector_index?: string;
  fulltext_index?: string;
  embed_model?: string;
  embed_dim?: number;
  lucene_query?: string;
  vector_cypher?: string;
  fulltext_cypher?: string;
  fusion?: string;
  vector_hits?: number;
  fulltext_hits?: number;
  pool?: number;
  top_k?: number;
  cypher?: string;
  keywords?: string[];
};

export type Fact = {
  label: string; etype: string; props: Record<string, any>;
  source?: string; rels?: { rel: string; target: string }[];
};

export type SearchResult = {
  answer: string;
  cypher: string;
  rows: any[];
  model_used: string;
  status?: "ok" | "llm_error" | "no_key" | "no_db" | "no_chunks" | "no_results";
  error?: string | null;
  keywords?: string[];
  retrieval_detail?: RetrievalDetail;
  facts?: Fact[];
};

export type CompareSide = {
  rows: any[];
  retrieval_detail?: RetrievalDetail;
  answer: string;
  model_used: string;
  status?: string;
  error?: string | null;
};
export type CompareResult = {
  question: string;
  status: "ok" | "no_db" | "no_chunks" | "no_vector";
  answer?: string;
  error?: string | null;
  vector?: CompareSide;
  hybrid?: CompareSide;
};

export function search(question: string, model?: string, answer_mode?: string) {
  return request<SearchResult>(
    "/search",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, model, answer_mode }),
    }
  );
}

export function compareSearch(question: string, model?: string, answer_mode?: string) {
  return request<CompareResult>("/search/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, model, answer_mode }),
  });
}

export function listDocuments() {
  return request<{ documents: any[] }>("/admin/documents");
}

export function uploadDocument(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  return request<any>("/admin/upload", { method: "POST", body: fd });
}

export function getGraph(docId?: string) {
  const qs = docId ? `?doc_id=${encodeURIComponent(docId)}` : "";
  return request<{ nodes: any[]; edges: any[] }>(`/admin/graph${qs}`);
}
