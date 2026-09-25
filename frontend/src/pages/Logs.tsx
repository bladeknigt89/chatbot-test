import { FormEvent, useEffect, useState } from "react";
import { Agent, ChatInteractionLog, api } from "../services/api";

type Tab = "audit" | "chat";

export default function Logs() {
  const [tab, setTab] = useState<Tab>("chat");
  const [rows, setRows] = useState<Array<Record<string, string>>>([]);
  const [chatRows, setChatRows] = useState<ChatInteractionLog[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [action, setAction] = useState("");
  const [resource, setResource] = useState("");
  const [agentId, setAgentId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  async function loadAudit(event?: FormEvent) {
    event?.preventDefault();
    const params = new URLSearchParams();
    if (action) params.set("action", action);
    if (resource) params.set("resource_type", resource);
    if (dateFrom) params.set("date_from", new Date(dateFrom).toISOString());
    if (dateTo) params.set("date_to", new Date(dateTo).toISOString());
    setRows(await api.logs(params));
  }

  async function loadChat(event?: FormEvent) {
    event?.preventDefault();
    const params = new URLSearchParams();
    if (agentId) params.set("agent_id", agentId);
    if (dateFrom) params.set("date_from", new Date(dateFrom).toISOString());
    if (dateTo) params.set("date_to", new Date(dateTo).toISOString());
    setChatRows(await api.chatLogs(params));
  }

  useEffect(() => {
    api.agents().then(setAgents).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (tab === "audit") void loadAudit();
    else void loadChat();
  }, [tab]);

  return (
    <div>
      <div className="page-title">
        <div>
          <h2>Naplók</h2>
          <p>Audit események és külön chat üzenetnapló.</p>
        </div>
      </div>
      <div className="row" style={{ marginBottom: 16, gap: 8 }}>
        <button
          type="button"
          className={`btn ${tab === "chat" ? "" : "ghost"}`}
          onClick={() => setTab("chat")}
        >
          Chat napló
        </button>
        <button
          type="button"
          className={`btn ${tab === "audit" ? "" : "ghost"}`}
          onClick={() => setTab("audit")}
        >
          Audit napló
        </button>
      </div>

      {tab === "chat" ? (
        <>
          <form className="card row" onSubmit={loadChat} style={{ marginBottom: 16, padding: 16 }}>
            <select value={agentId} onChange={(e) => setAgentId(e.target.value)}>
              <option value="">összes agent</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            <button className="btn" type="submit">
              Szűrés
            </button>
          </form>
          <div className="card" style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Idő</th>
                  <th>Agent</th>
                  <th>Token</th>
                  <th>API kulcs neve</th>
                  <th>IP</th>
                  <th>Kliens</th>
                  <th>Kérdés</th>
                  <th>Válasz</th>
                </tr>
              </thead>
              <tbody>
                {chatRows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.timestamp ? new Date(row.timestamp).toLocaleString("hu-HU") : "—"}</td>
                    <td>{row.agent_name || row.agent_id}</td>
                    <td>{row.token_label || "—"}</td>
                    <td>{row.api_key_name || "—"}</td>
                    <td>{row.ip || "—"}</td>
                    <td title={row.client} style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {row.client || "—"}
                    </td>
                    <td style={{ maxWidth: 240, whiteSpace: "pre-wrap" }}>{row.question || "—"}</td>
                    <td style={{ maxWidth: 320, whiteSpace: "pre-wrap" }}>{row.answer || "—"}</td>
                  </tr>
                ))}
                {chatRows.length === 0 && (
                  <tr>
                    <td colSpan={8} className="muted">
                      Nincs chat naplóbejegyzés. Kapcsold be az agent „Chat napló” beállításait.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <>
          <form className="card row" onSubmit={loadAudit} style={{ marginBottom: 16, padding: 16 }}>
            <input placeholder="action" value={action} onChange={(e) => setAction(e.target.value)} />
            <input
              placeholder="resource"
              value={resource}
              onChange={(e) => setResource(e.target.value)}
            />
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            <button className="btn" type="submit">
              Szűrés
            </button>
          </form>
          <div className="card">
            <table className="table">
              <thead>
                <tr>
                  <th>Idő</th>
                  <th>Felhasználó</th>
                  <th>Action</th>
                  <th>Erőforrás</th>
                  <th>Részletek</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.timestamp}</td>
                    <td>{row.user}</td>
                    <td>{row.action}</td>
                    <td>
                      {row.resource_type} {row.resource_id}
                    </td>
                    <td>{row.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
