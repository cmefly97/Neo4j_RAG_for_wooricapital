import { useState } from "react";
import UserTab from "./tabs/UserTab";
import AdminTab from "./tabs/AdminTab";

export default function App() {
  const [tab, setTab] = useState<"user" | "admin">("user");
  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 1100, margin: "0 auto", padding: 16 }}>
      <h2>오토운영팀 지식그래프 검색 (PoC)</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button onClick={() => setTab("user")} disabled={tab === "user"}>사용자</button>
        <button onClick={() => setTab("admin")} disabled={tab === "admin"}>관리자</button>
      </div>
      {tab === "user" ? <UserTab /> : <AdminTab />}
    </div>
  );
}
