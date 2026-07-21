import { useEffect, useState } from "react";
import {
  search, compareSearch, listModels,
  ModelInfo, SearchResult, CompareResult, RetrievalDetail, Fact,
} from "../api/client";
import FactsGraph from "../components/FactsGraph";

const EXAMPLES = [
  "론/할부 상품 취급 가능 개월수가 어떻게돼?",
  "론/할부 나이스 885점, 금리등급 2등급일 때 적용 될 수 있는 최저 금리 알려줘",
  "듀얼상품 금리등급 몇등급까지 취급 가능해?",
  "엔카 슬라이딩 가능해?",
  "신용구제 상품에서 신용회복, 개인회생 고객인데 판정값이 R 판정이야",
];

const META = new Set(["id", "origin", "label", "etype", "source_file", "norm_label", "community", "file_type"]);

function mdToHtml(md: string): string {
  const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const inline = (t: string) =>
    esc(t).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+?)`/g, "<code>$1</code>");
  const lines = (md || "").replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let list: "ul" | "ol" | null = null;
  const close = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) { close(); continue; }
    let m: RegExpMatchArray | null;
    if ((m = line.match(/^(#{1,4})\s+(.*)$/))) {
      const lv = Math.min(m[1].length + 2, 6); close(); out.push(`<h${lv}>${inline(m[2])}</h${lv}>`);
    } else if ((m = line.match(/^\s*[-*•]\s+(.*)$/))) {
      if (list !== "ul") { close(); out.push("<ul>"); list = "ul"; } out.push(`<li>${inline(m[1])}</li>`);
    } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
      if (list !== "ol") { close(); out.push("<ol>"); list = "ol"; } out.push(`<li>${inline(m[1])}</li>`);
    } else { close(); out.push(`<p>${inline(line)}</p>`); }
  }
  close();
  return out.join("\n");
}

type Explain = { kind: "error" | "warn" | "info"; title: string; detail: string; hint: string; fallback?: boolean };
function explain(status?: string, error?: string): Explain | null {
  const e = error || "";
  if (status === "no_db") return { kind: "error", title: "데이터베이스에 연결할 수 없어요", detail: "Neo4j 서버에 연결하지 못했습니다.", hint: "백엔드 실행·VPN·방화벽·.env(NEO4J_URI)를 확인하세요." };
  if (status === "no_vector") return { kind: "info", title: "벡터 검색이 준비되지 않았어요", detail: "비교하려면 임베딩·벡터 인덱스가 필요합니다.", hint: "백엔드에서 setup_hybrid 를 먼저 실행하세요." };
  if (status === "llm_error") {
    let hint = "잠시 후 다시 시도해 보세요. 문제가 계속되면 모델 서버 상태를 확인하세요.";
    if (/ratelimit|rate.?limit|429/i.test(e)) hint = "요청이 몰려 일시 제한(RateLimit)됐습니다. 잠시 후 재시도하세요.";
    else if (/timeout|connect|network|gateway/i.test(e)) hint = "모델 게이트웨이 연결이 지연/실패했습니다. 사내망/VPN을 확인하세요.";
    else if (/401|403|auth|api key|unauthorized/i.test(e)) hint = "모델 인증 실패. .env의 API 키를 확인하세요.";
    return { kind: "warn", title: "AI 답변 생성에 실패했어요", detail: e || "모델 호출 중 오류가 발생했습니다.", hint, fallback: true };
  }
  if (status === "no_key") return { kind: "info", title: "AI 요약을 생략했어요", detail: "모델의 API 키가 없습니다.", hint: ".env에 HCX30_API_KEY를 넣으세요.", fallback: true };
  if (status === "no_results") return { kind: "info", title: "관련 내용을 찾지 못했어요", detail: "검색된 문서가 없습니다.", hint: "질문 표현을 바꿔 보세요." };
  if (status === "no_chunks") return { kind: "info", title: "적재된 문서가 없어요", detail: "검색할 데이터가 비어 있습니다.", hint: "ingest_source → setup_hybrid 를 먼저 실행하세요." };
  return null;
}
const BANNER: Record<Explain["kind"], { bg: string; bd: string; fg: string; icon: string }> = {
  error: { bg: "#fdecea", bd: "#f5c6cb", fg: "#a12622", icon: "⛔" },
  warn: { bg: "#fff8e6", bd: "#ffe1a6", fg: "#8a6100", icon: "⚠️" },
  info: { bg: "#eef4fb", bd: "#cfe0f3", fg: "#2b5a8c", icon: "ℹ️" },
};
function Banner({ info }: { info: Explain }) {
  const c = BANNER[info.kind];
  return (
    <div style={{ background: c.bg, border: `1px solid ${c.bd}`, color: c.fg, borderRadius: 8, padding: "10px 12px", marginBottom: 10 }}>
      <div style={{ fontWeight: 700, marginBottom: 3, fontSize: 14 }}>{c.icon} {info.title}</div>
      <div style={{ fontSize: 12.5, opacity: 0.95 }}>{info.detail}</div>
      {info.hint && <div style={{ fontSize: 12, marginTop: 5, opacity: 0.85 }}>💡 {info.hint}</div>}
    </div>
  );
}
function Field({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ fontSize: 12, color: "#8a94a0", marginBottom: 3 }}>{label}</div>
      <pre style={{ margin: 0, background: "#f6f8fa", border: "1px solid #eef0f2", borderRadius: 6, padding: 10, fontSize: 12, lineHeight: 1.5, whiteSpace: "pre-wrap", color: "#33404d" }}>{value}</pre>
    </div>
  );
}
function RetrievalView({ d }: { d: RetrievalDetail }) {
  const isHybrid = d.mode === "hybrid";
  const isVec = d.mode === "vector";
  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <span className="chip" style={{ background: isHybrid ? "#e7f3ec" : "#eef2f6", borderColor: isHybrid ? "#bfe2cc" : "#dde3ea", color: isHybrid ? "#1c7a43" : "#39506b" }}>
          {isHybrid ? "🔀 Hybrid (벡터+풀텍스트)" : isVec ? "🧭 벡터 검색" : "🔤 키워드 검색"}
        </span>
        {isHybrid && <span style={{ fontSize: 12, color: "#8a94a0", marginLeft: 8 }}>벡터 {d.vector_hits}건 · 풀텍스트 {d.fulltext_hits}건 → {d.fusion}</span>}
      </div>
      {d.steps && (
        <ol style={{ margin: "6px 0 10px", paddingLeft: 20, fontSize: 13, color: "#3a4654", lineHeight: 1.7 }}>
          {d.steps.map((s, i) => <li key={i}>{s.replace(/^\d+\)\s*/, "")}</li>)}
        </ol>
      )}
      <details>
        <summary>실제 쿼리 보기</summary>
        <div style={{ marginTop: 6 }}>
          {d.embed_model && <Field label={`임베딩 (${d.embed_model}, ${d.embed_dim}차원)`} value={`벡터 인덱스: ${d.vector_index}`} />}
          {d.lucene_query && <Field label="풀텍스트 질의 (Lucene)" value={d.lucene_query} />}
          {d.vector_cypher && <Field label="벡터 검색 Cypher" value={d.vector_cypher} />}
          {d.fulltext_cypher && <Field label="풀텍스트 검색 Cypher" value={d.fulltext_cypher} />}
          {d.cypher && <Field label="Cypher" value={d.cypher} />}
          {d.keywords && <Field label="키워드" value={d.keywords.join(", ")} />}
        </div>
      </details>
    </div>
  );
}
function FactsView({ facts, onGraph }: { facts: Fact[]; onGraph: (f: Fact[]) => void }) {
  return (
    <div style={{ marginTop: 14, padding: "10px 12px", background: "#f3f7f4", border: "1px solid #d8e8de", borderRadius: 8 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: "#1c7a43", fontWeight: 700 }}>🧩 구조화 사실 (그래프)</span>
        <button onClick={() => onGraph(facts)} style={{ fontSize: 11.5, border: "1px solid #bfe2cc", background: "#e7f3ec", color: "#1c7a43", borderRadius: 14, padding: "3px 10px", cursor: "pointer" }}>🕸 그래프보기</button>
      </div>
      {facts.map((f, i) => {
        const props = Object.entries(f.props || {}).filter(([k]) => !META.has(k));
        return (
          <div key={i} style={{ padding: "5px 0", borderTop: i ? "1px solid #e3efe8" : "none" }}>
            <span className="chip" style={{ background: "#e7f3ec", borderColor: "#bfe2cc", color: "#1c7a43", marginRight: 6 }}>{f.etype}</span>
            <strong style={{ fontSize: 13 }}>{f.label}</strong>
            <div style={{ marginTop: 4, display: "flex", flexWrap: "wrap", gap: 4 }}>
              {props.map(([k, v]) => <span key={k} className="chip" style={{ fontSize: 11 }}>{k}: {String(v)}</span>)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

type Answerable = { answer: string; model_used: string; status?: string; error?: string | null; rows?: any[]; facts?: Fact[] };
function AnswerCard({ data, compact, onSource, onGraph }: { data: Answerable; compact?: boolean; onSource: (s: string, rows: any[]) => void; onGraph: (f: Fact[]) => void }) {
  const info = explain(data.status, data.error || undefined);
  const showExcerpt = info?.fallback;
  const sources: string[] = Array.from(new Set((data.rows || []).map((r) => r.source).filter(Boolean)));
  return (
    <div className="card" style={compact ? { padding: "14px 16px" } : {}}>
      {info && <Banner info={info} />}
      {data.status !== "no_results" && (<>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <strong style={{ fontSize: 14 }}>{showExcerpt ? "📄 문서 발췌" : "💬 답변"}</strong>
          <span style={{ fontSize: 11.5, color: "#8a94a0" }}>{data.model_used}</span>
        </div>
        {showExcerpt
          ? <pre style={{ whiteSpace: "pre-wrap", margin: 0, fontSize: 13, lineHeight: 1.6, color: "#33404d", background: "#fafbfc", border: "1px solid #eef0f2", borderRadius: 8, padding: 12 }}>{data.answer}</pre>
          : <div className="ans" dangerouslySetInnerHTML={{ __html: mdToHtml(data.answer) }} />}
        {data.facts && data.facts.length > 0 && <FactsView facts={data.facts} onGraph={onGraph} />}
        {sources.length > 0 && (
          <div style={{ marginTop: 14, paddingTop: 10, borderTop: "1px dashed #e3e6ea" }}>
            <div style={{ fontSize: 12, color: "#8a94a0", marginBottom: 6 }}>📎 출처 (클릭하면 관련 내용)</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {sources.map((s) => <span key={s} className="chip chip-btn" onClick={() => onSource(s, data.rows || [])}>📄 {s}</span>)}
            </div>
          </div>
        )}
      </>)}
    </div>
  );
}

export default function UserTab() {
  const [q, setQ] = useState("");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [model, setModel] = useState<string>("");
  const [compareMode, setCompareMode] = useState(false);
  const [answerMode, setAnswerMode] = useState<"concise" | "standard" | "detailed" | "counselor">("standard");
  const [res, setRes] = useState<SearchResult | null>(null);
  const [cmp, setCmp] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [popup, setPopup] = useState<{ source: string; rows: any[] } | null>(null);
  const [graphFacts, setGraphFacts] = useState<Fact[] | null>(null);

  useEffect(() => {
    listModels().then((ms) => {
      setModels(ms);
      const def = ms.find((m) => m.default) ?? ms[0];
      if (def) setModel(def.id);
    }).catch((e) => setError(String(e.message ?? e)));
  }, []);

  async function runSearch(question: string) {
    if (!question.trim()) return;
    setLoading(true); setError(null); setRes(null); setCmp(null); setPopup(null);
    try {
      if (compareMode) setCmp(await compareSearch(question, model, answerMode));
      else setRes(await search(question, model, answerMode));
    } catch (e: any) { setError(String(e.message ?? e)); }
    finally { setLoading(false); }
  }
  const onExample = (ex: string) => { setQ(ex); runSearch(ex); };
  const onSource = (source: string, rows: any[]) => setPopup({ source, rows: rows.filter((r) => r.source === source) });

  return (
    <div>
      <style>{`
        .ans { line-height:1.7; color:#1f2328; font-size:15px; }
        .ans h3,.ans h4,.ans h5 { margin:14px 0 6px; } .ans p { margin:8px 0; }
        .ans ul,.ans ol { margin:8px 0; padding-left:22px; } .ans li { margin:4px 0; }
        .ans code { background:#f0f1f3; padding:1px 5px; border-radius:4px; font-size:13px; }
        .ans strong { color:#0b2942; }
        .card { border:1px solid #e3e6ea; border-radius:12px; padding:18px 20px; background:#fff; box-shadow:0 1px 3px rgba(0,0,0,.04); }
        .chip { font-size:12px; background:#eef2f6; border:1px solid #dde3ea; border-radius:14px; padding:3px 10px; color:#39506b; display:inline-block; }
        .chip-btn { cursor:pointer; } .chip-btn:hover { background:#dce9f7; border-color:#bcd4ee; }
        details>summary { cursor:pointer; color:#5b6b7c; font-size:13px; padding:6px 0; }
        .cols { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
        @media (max-width:820px){ .cols { grid-template-columns:1fr; } }
        .overlay { position:fixed; inset:0; background:rgba(0,0,0,.4); display:flex; align-items:center; justify-content:center; z-index:50; }
        .modal { background:#fff; border-radius:12px; max-width:760px; width:90%; max-height:80vh; overflow:auto; padding:20px 22px; box-shadow:0 10px 40px rgba(0,0,0,.25); }
      `}</style>

      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8, flexWrap: "wrap" }}>
        <span>🤖 모델</span>
        <span className="chip" style={{ background: "#eef2f6", fontWeight: 600 }}>
          {models.find((m) => m.id === model)?.label ?? "HCX-30B-Text"}
        </span>
        <label style={{ marginLeft: 8, fontSize: 13, color: "#3a4654", cursor: "pointer", userSelect: "none" }}>
          <input type="checkbox" checked={compareMode} onChange={(e) => setCompareMode(e.target.checked)} style={{ marginRight: 5 }} />
          🔬 벡터 vs Hybrid 비교
        </label>
        <span style={{ marginLeft: 12, fontSize: 13, color: "#3a4654" }}>✍️ 답변 스타일</span>
        <select value={answerMode} onChange={(e) => setAnswerMode(e.target.value as any)} style={{ padding: 6 }}
          title="답변의 길이·상세함 선택">
          <option value="concise">간단히 (핵심만)</option>
          <option value="standard">기본</option>
          <option value="detailed">자세히 (조건·수치 상세)</option>
          <option value="counselor">상담 보조원</option>
        </select>
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <input style={{ flex: 1, padding: 8 }} placeholder="예: 듀얼상품 금리등급 몇등급까지 취급 가능해?"
          value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && runSearch(q)} />
        <button onClick={() => runSearch(q)} disabled={loading}>{loading ? "검색 중…" : "검색"}</button>
      </div>

      <div style={{ marginTop: 10 }}>
        <div style={{ fontSize: 12, color: "#888", marginBottom: 6 }}>💡 예시 질문 (클릭하면 검색)</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {EXAMPLES.map((ex) => (
            <button key={ex} onClick={() => onExample(ex)} disabled={loading} title={ex}
              style={{ padding: "6px 10px", fontSize: 12, border: "1px solid #d0d7de", background: "#f6f8fa", borderRadius: 16, cursor: "pointer", maxWidth: 360, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {ex}
            </button>
          ))}
        </div>
      </div>

      {error && <div style={{ marginTop: 12 }}><Banner info={{ kind: "error", title: "검색 요청에 실패했어요", detail: error, hint: "백엔드(uvicorn)가 실행 중인지 확인하세요." }} /></div>}

      {/* 단일 검색 */}
      {res && (
        <div style={{ marginTop: 16 }}>
          {(() => { const info = explain(res.status, res.error || undefined); const hard = res.status === "no_db" || res.status === "no_results" || res.status === "no_chunks"; return (
            <>
              {hard && info && <Banner info={info} />}
              {!hard && <AnswerCard data={res} onSource={onSource} onGraph={setGraphFacts} />}
              {res.retrieval_detail && (
                <div style={{ marginTop: 12 }}><details open><summary>🔎 검색 과정 / 쿼리 상세</summary>
                  <div style={{ marginTop: 8, padding: "10px 12px", background: "#fbfcfd", border: "1px solid #eef0f2", borderRadius: 8 }}><RetrievalView d={res.retrieval_detail} /></div>
                </details></div>
              )}
              {!!res.rows?.length && (
                <div style={{ marginTop: 12 }}><details><summary>📚 근거 청크 ({res.rows.length})</summary>
                  <div style={{ marginTop: 8 }}>{res.rows.map((r, i) => (
                    <div key={i} style={{ border: "1px solid #eef0f2", borderRadius: 8, padding: 12, marginBottom: 8 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                        <span className="chip chip-btn" onClick={() => onSource(r.source, res.rows)}>📄 {r.source}{r.locator ? ` / ${r.locator}` : ""}</span>
                        {typeof r.score === "number" && <span style={{ fontSize: 11, color: "#9aa4af" }}>score {r.score}</span>}
                      </div>
                      <div style={{ fontSize: 13, color: "#3a4654", whiteSpace: "pre-wrap", maxHeight: 110, overflow: "auto" }}>{(r.text || "").slice(0, 500)}</div>
                    </div>
                  ))}</div>
                </details></div>
              )}
            </>
          ); })()}
        </div>
      )}

      {/* 비교 검색 */}
      {cmp && (
        <div style={{ marginTop: 16 }}>
          {cmp.status !== "ok" ? (
            <Banner info={explain(cmp.status, cmp.error || undefined) ?? { kind: "info", title: "비교할 수 없어요", detail: cmp.answer || "", hint: "" }} />
          ) : (
            <>
              <div style={{ fontSize: 13, color: "#5b6b7c", marginBottom: 10 }}>
                같은 질문을 <strong>벡터 검색만</strong> vs <strong>Hybrid(벡터+풀텍스트)</strong>로 비교합니다.
              </div>
              <div className="cols">
                {(["vector", "hybrid"] as const).map((key) => {
                  const side = cmp[key]; if (!side) return null;
                  return (
                    <div key={key}>
                      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8 }}>
                        {key === "vector" ? "🧭 벡터 검색만" : "🔀 Hybrid (벡터+풀텍스트)"}
                      </div>
                      <AnswerCard data={side} compact onSource={onSource} onGraph={setGraphFacts} />
                      {side.retrieval_detail && (
                        <details style={{ marginTop: 8 }}><summary>🔎 검색 상세</summary>
                          <div style={{ marginTop: 6, padding: "10px 12px", background: "#fbfcfd", border: "1px solid #eef0f2", borderRadius: 8 }}><RetrievalView d={side.retrieval_detail} /></div>
                        </details>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}

      {/* 관계 그래프 팝업 */}
      {graphFacts && (
        <div className="overlay" onClick={() => setGraphFacts(null)}>
          <div className="modal" style={{ maxWidth: 900 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <strong style={{ fontSize: 15 }}>🕸 구조화 사실 관계 그래프</strong>
              <button onClick={() => setGraphFacts(null)} style={{ border: "none", background: "transparent", fontSize: 20, cursor: "pointer", color: "#888" }}>✕</button>
            </div>
            <div style={{ fontSize: 12, color: "#8a94a0", marginBottom: 8 }}>
              엔티티 {graphFacts.length}개 · 노드를 드래그해 볼 수 있습니다. 색 = 유형(Product·RateGrade·Decision·Nego·VehicleCondition·HandlingRule)
            </div>
            <FactsGraph facts={graphFacts} />
          </div>
        </div>
      )}

      {/* 출처 팝업 */}
      {popup && (
        <div className="overlay" onClick={() => setPopup(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <strong style={{ fontSize: 15 }}>📄 {popup.source}</strong>
              <button onClick={() => setPopup(null)} style={{ border: "none", background: "transparent", fontSize: 20, cursor: "pointer", color: "#888" }}>✕</button>
            </div>
            <div style={{ fontSize: 12, color: "#8a94a0", marginBottom: 10 }}>이 답변과 연관된 내용 {popup.rows.length}건</div>
            {popup.rows.map((r, i) => (
              <div key={i} style={{ borderTop: "1px solid #eee", padding: "10px 0" }}>
                {r.locator && <div style={{ fontSize: 12, color: "#8a94a0", marginBottom: 4 }}>위치: {r.locator}{typeof r.score === "number" ? ` · score ${r.score}` : ""}</div>}
                <div style={{ fontSize: 13.5, lineHeight: 1.6, color: "#2b333c", whiteSpace: "pre-wrap" }}>{r.text}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
