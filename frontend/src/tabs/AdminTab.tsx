import { useEffect, useState } from "react";
import { listDocuments, uploadDocument, getGraph } from "../api/client";
import GraphView from "../components/GraphView";

export default function AdminTab() {
  const [docs, setDocs] = useState<any[]>([]);
  const [graph, setGraph] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      setDocs((await listDocuments()).documents ?? []);
      setGraph(await getGraph());
    } catch (e: any) {
      console.error("[ADMIN] 새로고침 실패:", e);
      setError(String(e.message ?? e));
    }
  }
  useEffect(() => { refresh(); }, []);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    console.info(`[ADMIN] 업로드: ${file.name}`);
    try {
      await uploadDocument(file);
      await refresh();
    } catch (err: any) {
      console.error("[ADMIN] 업로드 실패:", err);
      setError(String(err.message ?? err));
    }
  }

  return (
    <div>
      {error && (
        <div style={{ marginBottom: 12, padding: 12, background: "#fdecea",
                      border: "1px solid #f5c6cb", color: "#a12622", borderRadius: 4 }}>
          ⚠️ {error}
        </div>
      )}

      <h4>문서 업로드 (xlsx, docx, pdf, md)</h4>
      <input type="file" accept=".xlsx,.docx,.pdf,.md" onChange={onUpload} />

      <h4 style={{ marginTop: 16 }}>업로드된 문서</h4>
      <table border={1} cellPadding={6} style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead><tr><th>파일명</th><th>형식</th><th>상태</th></tr></thead>
        <tbody>
          {docs.map((d) => (
            <tr key={d.name}><td>{d.name}</td><td>{d.type}</td><td>{d.status}</td></tr>
          ))}
        </tbody>
      </table>

      <h4 style={{ marginTop: 16 }}>그래프 뷰</h4>
      <GraphView nodes={graph.nodes} edges={graph.edges} />
    </div>
  );
}
