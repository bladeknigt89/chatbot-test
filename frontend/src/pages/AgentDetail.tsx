import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import AgentActions from "../components/AgentActions";
import ChatLogToggles from "../components/ChatLogToggles";
import { agentSettingsPayload } from "../components/agentPayload";
import DocumentDropzone from "../components/DocumentDropzone";
import { DocumentStatus, isProcessingDoc } from "../components/DocumentStatus";
import { Agent, DocumentItem, api } from "../services/api";

export default function AgentDetail() {
  const { id = "" } = useParams();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [message, setMessage] = useState("");
  const [sessionId, setSessionId] = useState<string>();
  const [chat, setChat] = useState<Array<{ role: string; text: string }>>([]);
  const [error, setError] = useState("");
  const [saveMessage, setSaveMessage] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    const [nextAgent, nextDocs] = await Promise.all([api.agent(id), api.agentDocuments(id)]);
    setAgent(nextAgent);
    setDocs(nextDocs);
  }

  async function refreshDocs() {
    setDocs(await api.agentDocuments(id));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [id]);

  // Csak a dokumentum státuszt polloljuk — az agent űrlapot ne írjuk felül szerkesztés közben.
  useEffect(() => {
    const busy = docs.some(isProcessingDoc);
    const timer = setInterval(() => refreshDocs().catch(() => undefined), busy ? 1500 : 4000);
    return () => clearInterval(timer);
  }, [id, docs]);

  const snippet = useMemo(() => {
    if (!agent) return "";
    return `<script src="${window.location.origin}/chat-widget.js" data-agent="${agent.id}" data-api-key="YOUR_API_KEY"></script>`;
  }, [agent]);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!agent) return;
    setSaving(true);
    setSaveMessage("");
    setError("");
    try {
      const updated = await api.updateAgent(agent.id, agentSettingsPayload(agent));
      setAgent(updated);
      setSaveMessage("Mentve.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mentés sikertelen.");
    } finally {
      setSaving(false);
    }
  }

  async function upload(files: FileList) {
    for (const file of Array.from(files)) {
      await api.upload(id, file);
    }
    await load();
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;
    const userText = message;
    setChat((current) => [...current, { role: "user", text: userText }]);
    setMessage("");
    const result = await api.chat(id, userText, sessionId);
    setSessionId(result.session_id);
    const sources = result.sources
      .map((src) => `${src.document_name}${src.page_number ? ` – ${src.page_number}. oldal` : ""}`)
      .join("\n");
    setChat((current) => [
      ...current,
      { role: "bot", text: sources ? `${result.message}\n\nForrás:\n${sources}` : result.message }
    ]);
  }

  if (!agent) return <div>{error || "Betöltés…"}</div>;

  return (
    <div>
      <div className="page-title">
        <div>
          <h2>{agent.name}</h2>
          <p>Tudásbázis, widget és próba chat.</p>
        </div>
      </div>
      <div className="card" style={{ marginBottom: 16 }}>
        <AgentActions agent={agent} onUpdated={load} />
      </div>
      <div className="grid">
        <form className="card form" onSubmit={save}>
          <h3>Alapadatok</h3>
          <label>
            Név
            <input value={agent.name} onChange={(e) => setAgent({ ...agent, name: e.target.value })} />
          </label>
          <label>
            Leírás
            <textarea value={agent.description} onChange={(e) => setAgent({ ...agent, description: e.target.value })} />
          </label>
          <label>
            System prompt
            <textarea
              rows={5}
              value={agent.system_prompt}
              onChange={(e) => setAgent({ ...agent, system_prompt: e.target.value })}
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={agent.show_sources !== false}
              onChange={(e) => setAgent({ ...agent, show_sources: e.target.checked })}
            />
            <span>Forrásfájlok megjelenítése a válaszban</span>
          </label>
          <label>
            Tudásprofil
            <select
              value={agent.knowledge_profile || "auto"}
              onChange={(e) =>
                setAgent({
                  ...agent,
                  knowledge_profile: e.target.value as Agent["knowledge_profile"],
                })
              }
            >
              <option value="auto">auto (dokumentumokból)</option>
              <option value="general">általános / egyetem / support</option>
              <option value="rpg">szerepjáték / világkatalógus</option>
            </select>
          </label>
          <h3>Chat napló</h3>
          <ChatLogToggles
            agent={agent}
            onChange={(next) =>
              setAgent((prev) => {
                if (!prev) return prev;
                return typeof next === "function" ? next(prev) : next;
              })
            }
          />
          <h3>Chat tulajdonságok</h3>
          <label>
            Widget szín
            <div className="row">
              <input
                type="color"
                value={agent.widget_primary_color || "#c45c26"}
                onChange={(e) => setAgent({ ...agent, widget_primary_color: e.target.value })}
                style={{ width: 48, padding: 4 }}
              />
              <input
                value={agent.widget_primary_color}
                onChange={(e) => setAgent({ ...agent, widget_primary_color: e.target.value })}
              />
            </div>
          </label>
          <label>
            Widget cím
            <input value={agent.widget_title} onChange={(e) => setAgent({ ...agent, widget_title: e.target.value })} />
          </label>
          <label>
            Pozíció
            <select
              value={agent.widget_position}
              onChange={(e) => setAgent({ ...agent, widget_position: e.target.value })}
            >
              <option value="right">jobb</option>
              <option value="left">bal</option>
            </select>
          </label>
          <label>
            Üdvözlő üzenet
            <textarea
              value={agent.widget_welcome_message}
              onChange={(e) => setAgent({ ...agent, widget_welcome_message: e.target.value })}
            />
          </label>
          {error && <div className="error">{error}</div>}
          {saveMessage && <div className="success">{saveMessage}</div>}
          <button className="btn" type="submit" disabled={saving}>
            {saving ? "Mentés…" : "Mentés"}
          </button>
        </form>
        <div className="card">
          <h3>Dokumentumok</h3>
          <DocumentDropzone hint="Több fájl is kiválasztható egyszerre, fájlonként maximum 500 MB." onFiles={upload} />
          <table className="table">
            <thead>
              <tr>
                <th>Fájl</th>
                <th>Státusz</th>
                <th>Chunkok</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.id}>
                  <td>
                    {doc.original_filename}
                    {doc.error_message && <div className="error">{doc.error_message}</div>}
                  </td>
                  <td>
                    <DocumentStatus doc={doc} />
                  </td>
                  <td>{doc.status === "READY" ? doc.chunk_count : "—"}</td>
                  <td className="row">
                    <button className="btn ghost" onClick={() => api.reprocess(id, doc.id).then(load)}>
                      Újrafeldolgozás
                    </button>
                    <button className="btn danger" onClick={() => api.deleteDocument(id, doc.id).then(load)}>
                      Törlés
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="grid" style={{ marginTop: 16 }}>
        <div className="card">
          <h3>Próba chat</h3>
          <div className="chat-log">
            {chat.map((item, index) => (
              <div className={`bubble ${item.role === "user" ? "user" : "bot"}`} key={index}>
                {item.text}
              </div>
            ))}
          </div>
          <form className="form" onSubmit={send} style={{ marginTop: 12 }}>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Tegyen fel egy magyar kérdést…"
            />
            <button className="btn" type="submit">
              Küldés
            </button>
          </form>
        </div>
        <div className="card">
          <h3>Beágyazható widget</h3>
          <p className="muted">A részletes embed generátor a fenti „Embed kód” gombbal érhető el.</p>
          <pre className="code">{snippet}</pre>
        </div>
      </div>
    </div>
  );
}
