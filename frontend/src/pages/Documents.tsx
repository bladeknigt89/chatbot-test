import { useEffect, useState } from "react";
import { DocumentStatus, isProcessingDoc } from "../components/DocumentStatus";
import { Agent, DocumentItem, api } from "../services/api";

export default function Documents() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState("");
  const [drag, setDrag] = useState(false);

  async function load() {
    const [nextDocs, nextAgents] = await Promise.all([api.documents(), api.agents()]);
    setDocs(nextDocs);
    setAgents(nextAgents);
    if (!agentId && nextAgents[0]) setAgentId(nextAgents[0].id);
  }

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  useEffect(() => {
    const busy = docs.some(isProcessingDoc);
    const timer = setInterval(() => load().catch(() => undefined), busy ? 1500 : 4000);
    return () => clearInterval(timer);
  }, [docs]);

  async function upload(files: FileList | null) {
    if (!files || !agentId) return;
    for (const file of Array.from(files)) {
      await api.upload(agentId, file);
    }
    await load();
  }

  return (
    <div>
      <div className="page-title">
        <div>
          <h2>Dokumentumok</h2>
          <p>Feltöltés után a worker automatikusan feldolgozza a fájlokat.</p>
        </div>
      </div>
      <div className="card form" style={{ marginBottom: 16 }}>
        <label>
          Cél agent
          <select value={agentId} onChange={(e) => setAgentId(e.target.value)}>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </label>
        <div
          className={`dropzone ${drag ? "active" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            void upload(e.dataTransfer.files);
          }}
        >
          Húzza ide a dokumentumot, vagy tallózzon.
          <div>
            <input type="file" multiple accept=".pdf,.docx,.xlsx,.xls" onChange={(e) => void upload(e.target.files)} />
          </div>
        </div>
      </div>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Fájl</th>
              <th>Agent</th>
              <th>Státusz</th>
              <th>Chunkok</th>
              <th>Hiba</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {docs.map((doc) => (
              <tr key={doc.id}>
                <td>{doc.original_filename}</td>
                <td>{agents.find((item) => item.id === doc.agent_id)?.name || doc.agent_id}</td>
                <td>
                  <DocumentStatus doc={doc} />
                </td>
                <td>{doc.status === "READY" ? doc.chunk_count : "—"}</td>
                <td>{doc.error_message}</td>
                <td className="row">
                  <button className="btn ghost" onClick={() => api.reprocess(doc.agent_id, doc.id).then(load)}>
                    Újra
                  </button>
                  <button className="btn danger" onClick={() => api.deleteDocument(doc.agent_id, doc.id).then(load)}>
                    Törlés
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
