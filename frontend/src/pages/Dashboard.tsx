import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AgentActions from "../components/AgentActions";
import { Agent, api, Dashboard as DashboardData } from "../services/api";

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState("");

  async function load() {
    const [dash, list] = await Promise.all([api.dashboard(), api.agents()]);
    setData(dash);
    setAgents(list);
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <div>Betöltés…</div>;

  const cards = [
    ["Agentek száma", data.agent_count],
    ["Dokumentumok", data.document_count],
    ["Feldolgozás alatt", data.processing_document_count],
    ["API kulcsok", data.api_key_count],
    ["Mai chat kérések", data.chat_requests_today],
    ["Mai hibák", data.errors_today]
  ];

  return (
    <div>
      <div className="page-title">
        <div>
          <h2>Irányítópult</h2>
          <p>A helyi RAG platform aktuális állapota.</p>
        </div>
        <Link className="btn" to="/agents">
          Új agent
        </Link>
      </div>
      <div className="grid">
        {cards.map(([label, value]) => (
          <div className="card" key={String(label)}>
            <div className="muted">{label}</div>
            <div className="stat">{value}</div>
          </div>
        ))}
      </div>

      <div className="page-title" style={{ marginTop: 28 }}>
        <div>
          <h2>Agentek</h2>
          <p>Chat megnyitása, beágyazó kód és chat tulajdonságok agentenként.</p>
        </div>
      </div>
      <div className="card">
        {agents.length === 0 ? (
          <p className="muted">
            Még nincs agent. Hozzon létre egyet az <Link to="/agents">Agentek</Link> oldalon.
          </p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Név</th>
                <th>Státusz</th>
                <th>Dokumentumok</th>
                <th>Műveletek</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id}>
                  <td>
                    <Link to={`/agents/${agent.id}`}>{agent.name}</Link>
                    <div className="muted">{agent.description || agent.widget_title || "—"}</div>
                  </td>
                  <td>
                    <span className={`badge ${agent.status === "active" ? "ready" : "inactive"}`}>
                      {agent.status === "active" ? "aktív" : "inaktív"}
                    </span>
                  </td>
                  <td>{agent.document_count}</td>
                  <td>
                    <AgentActions agent={agent} onUpdated={load} compact />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
