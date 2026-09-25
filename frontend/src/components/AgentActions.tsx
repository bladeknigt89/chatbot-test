import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Agent, api } from "../services/api";

const STORAGE_PREFIX = "lac_agent_api_key:";

function savedKey(agentId: string): string {
  return localStorage.getItem(STORAGE_PREFIX + agentId) || "";
}

function storeKey(agentId: string, key: string) {
  if (key) localStorage.setItem(STORAGE_PREFIX + agentId, key);
}

function chatDemoUrl(agent: Agent, apiKey?: string): string {
  const params = new URLSearchParams({
    agent: agent.id,
    title: agent.widget_title || agent.name
  });
  if (apiKey) params.set("key", apiKey);
  return `${window.location.origin}/chat-demo.html?${params.toString()}`;
}

function buildEmbedCode(agent: Agent, apiKey: string): string {
  const origin = window.location.origin;
  const title = agent.widget_title || agent.name;
  const welcome = (agent.widget_welcome_message || "").replace(/\\/g, "\\\\").replace(/`/g, "\\`").replace(/\$/g, "\\$");
  return `<!-- Local AI Chatbot widget: ${agent.name} -->
<script>
window.ChatWidgetConfig = {
  primaryColor: "${agent.widget_primary_color || "#c45c26"}",
  title: "${title.replace(/"/g, '\\"')}",
  position: "${agent.widget_position || "right"}",
  welcomeMessage: "${welcome.replace(/"/g, '\\"')}"
};
</script>
<script
  src="${origin}/chat-widget.js"
  data-agent="${agent.id}"
  data-api-key="${apiKey || "YOUR_API_KEY"}"
  data-api-base="${origin}">
</script>`;
}

type Props = {
  agent: Agent;
  onUpdated?: () => void;
  compact?: boolean;
};

export default function AgentActions({ agent, onUpdated, compact }: Props) {
  const [propsOpen, setPropsOpen] = useState(false);
  const [embedOpen, setEmbedOpen] = useState(false);
  const [draft, setDraft] = useState(agent);
  const [apiKey, setApiKey] = useState(savedKey(agent.id));
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setDraft(agent);
    setApiKey(savedKey(agent.id));
  }, [agent]);

  const embedCode = useMemo(() => buildEmbedCode(draft, apiKey), [draft, apiKey]);

  function openChat() {
    const key = savedKey(agent.id) || apiKey;
    window.open(chatDemoUrl(agent, key || undefined), "_blank", "noopener,noreferrer");
  }

  async function saveProps(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await api.updateAgent(agent.id, {
        name: draft.name,
        description: draft.description,
        system_prompt: draft.system_prompt,
        status: draft.status,
        show_sources: draft.show_sources,
        knowledge_profile: draft.knowledge_profile || "auto",
        widget_primary_color: draft.widget_primary_color,
        widget_title: draft.widget_title,
        widget_position: draft.widget_position,
        widget_welcome_message: draft.widget_welcome_message
      });
      setMessage("Chat tulajdonságok mentve.");
      onUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mentés sikertelen.");
    } finally {
      setBusy(false);
    }
  }

  async function createKey() {
    setBusy(true);
    setError("");
    try {
      const created = await api.createKey(`widget-${agent.name}`.slice(0, 80));
      setApiKey(created.key);
      storeKey(agent.id, created.key);
      setMessage("Új API kulcs létrehozva. Másolja el most — később nem látszik.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kulcs létrehozása sikertelen.");
    } finally {
      setBusy(false);
    }
  }

  async function copyEmbed() {
    storeKey(agent.id, apiKey);
    await navigator.clipboard.writeText(embedCode);
    setMessage("Beágyazó kód a vágólapra másolva.");
  }

  return (
    <>
      <div className={`row agent-actions ${compact ? "compact" : ""}`}>
        <button type="button" className="btn secondary" onClick={openChat} disabled={agent.status !== "active"}>
          Chat megnyitása
        </button>
        <button type="button" className="btn ghost" onClick={() => { setEmbedOpen(true); setMessage(""); setError(""); }}>
          Embed kód
        </button>
        <button type="button" className="btn ghost" onClick={() => { setPropsOpen(true); setDraft(agent); setMessage(""); setError(""); }}>
          Chat tulajdonságok
        </button>
        <Link className="btn ghost" to={`/agents/${agent.id}`}>
          Részletek
        </Link>
      </div>

      {propsOpen && (
        <div className="modal-backdrop" onClick={() => setPropsOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>Chat tulajdonságok – {agent.name}</h3>
              <button type="button" className="btn ghost" onClick={() => setPropsOpen(false)}>Bezár</button>
            </div>
            <form className="form" onSubmit={saveProps}>
              <label>
                Widget cím
                <input
                  value={draft.widget_title}
                  onChange={(e) => setDraft({ ...draft, widget_title: e.target.value })}
                  placeholder={agent.name}
                />
              </label>
              <label>
                Üdvözlő üzenet
                <textarea
                  rows={3}
                  value={draft.widget_welcome_message}
                  onChange={(e) => setDraft({ ...draft, widget_welcome_message: e.target.value })}
                />
              </label>
              <label>
                Elsődleges szín
                <div className="row">
                  <input
                    type="color"
                    value={draft.widget_primary_color || "#c45c26"}
                    onChange={(e) => setDraft({ ...draft, widget_primary_color: e.target.value })}
                    style={{ width: 48, padding: 4 }}
                  />
                  <input
                    value={draft.widget_primary_color}
                    onChange={(e) => setDraft({ ...draft, widget_primary_color: e.target.value })}
                  />
                </div>
              </label>
              <label>
                Pozíció
                <select
                  value={draft.widget_position}
                  onChange={(e) => setDraft({ ...draft, widget_position: e.target.value })}
                >
                  <option value="right">jobb alsó</option>
                  <option value="left">bal alsó</option>
                </select>
              </label>
              <label>
                System prompt
                <textarea
                  rows={4}
                  value={draft.system_prompt}
                  onChange={(e) => setDraft({ ...draft, system_prompt: e.target.value })}
                  placeholder="Opcionális agent-specifikus utasítások…"
                />
              </label>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={draft.show_sources !== false}
                  onChange={(e) => setDraft({ ...draft, show_sources: e.target.checked })}
                />
                <span>Forrásfájlok megjelenítése a válaszban</span>
              </label>
              <label>
                Tudásprofil
                <select
                  value={draft.knowledge_profile || "auto"}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      knowledge_profile: e.target.value as Agent["knowledge_profile"],
                    })
                  }
                >
                  <option value="auto">auto (dokumentumokból)</option>
                  <option value="general">általános / egyetem / support</option>
                  <option value="rpg">szerepjáték / világkatalógus</option>
                </select>
              </label>
              <label>
                Státusz
                <select value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })}>
                  <option value="active">aktív</option>
                  <option value="inactive">inaktív</option>
                </select>
              </label>
              {error && <div className="error">{error}</div>}
              {message && <div className="success">{message}</div>}
              <div className="row">
                <button className="btn" type="submit" disabled={busy}>Mentés</button>
                <button className="btn ghost" type="button" onClick={openChat}>Chat megnyitása</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {embedOpen && (
        <div className="modal-backdrop" onClick={() => setEmbedOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>Embed kód – {agent.name}</h3>
              <button type="button" className="btn ghost" onClick={() => setEmbedOpen(false)}>Bezár</button>
            </div>
            <div className="form">
              <p className="muted">
                Illessze be a kódot a saját oldalára. A widget a <code>/chat-widget.js</code> fájlt tölti be.
              </p>
              <label>
                API kulcs a widgethez
                <input
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="lac_…"
                />
              </label>
              <div className="row">
                <button type="button" className="btn secondary" onClick={createKey} disabled={busy}>
                  Új API kulcs generálása
                </button>
                <button type="button" className="btn" onClick={copyEmbed}>
                  Kód másolása
                </button>
                <button type="button" className="btn ghost" onClick={openChat}>
                  Chat megnyitása
                </button>
              </div>
              {error && <div className="error">{error}</div>}
              {message && <div className="success">{message}</div>}
              <pre className="code">{embedCode}</pre>
              <p className="muted">
                Teljes oldalas demó:{" "}
                <a href={chatDemoUrl(agent, apiKey || undefined)} target="_blank" rel="noreferrer">
                  chat-demo.html
                </a>
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
