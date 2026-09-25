import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AgentActions from "../components/AgentActions";
import { Agent, api } from "../services/api";

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [knowledgeProfile, setKnowledgeProfile] = useState<Agent["knowledge_profile"]>("auto");
  const [error, setError] = useState("");

  async function load() {
    setAgents(await api.agents());
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    await api.createAgent({
      name,
      description,
      status: "active",
      knowledge_profile: knowledgeProfile || "auto",
    });
    setName("");
    setDescription("");
    setKnowledgeProfile("auto");
    await load();
  }

  async function toggle(agent: Agent) {
    await api.updateAgent(agent.id, { status: agent.status === "active" ? "inactive" : "active" });
    await load();
  }

  async function remove(agent: Agent) {
    if (!confirm(`Törli a(z) ${agent.name} agentet?`)) return;
    await api.deleteAgent(agent.id);
    await load();
  }

  return (
    <div>
      <div className="page-title">
        <div>
          <h2>Agentek</h2>
          <p>Külön tudásbázisok, külön chatbotok.</p>
        </div>
      </div>
      <div className="card form" style={{ marginBottom: 18 }}>
        <form className="form" onSubmit={create}>
          <label>
            Név
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Leírás
            <input value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          <label>
            Tudásprofil
            <select
              value={knowledgeProfile || "auto"}
              onChange={(e) =>
                setKnowledgeProfile(e.target.value as Agent["knowledge_profile"])
              }
            >
              <option value="auto">auto (dokumentumokból)</option>
              <option value="general">általános / egyetem / support</option>
              <option value="rpg">szerepjáték / világkatalógus</option>
            </select>
          </label>
          <button className="btn" type="submit">
            Agent létrehozása
          </button>
        </form>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="card">
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
                  <div className="muted">{agent.description}</div>
                </td>
                <td>
                  <span className={`badge ${agent.status === "active" ? "ready" : "inactive"}`}>
                    {agent.status === "active" ? "aktív" : "inaktív"}
                  </span>
                </td>
                <td>{agent.document_count}</td>
                <td>
                  <AgentActions agent={agent} onUpdated={load} compact />
                  <div className="row" style={{ marginTop: 8 }}>
                    <button className="btn ghost" onClick={() => toggle(agent)}>
                      {agent.status === "active" ? "Deaktiválás" : "Aktiválás"}
                    </button>
                    <button className="btn danger" onClick={() => remove(agent)}>
                      Törlés
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
