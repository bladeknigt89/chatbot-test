import { FormEvent, useEffect, useState } from "react";
import { api } from "../services/api";

export default function Settings() {
  const [data, setData] = useState<Record<string, string | number | boolean> | null>(null);
  const [saved, setSaved] = useState("");

  useEffect(() => {
    api.settings().then(setData).catch(() => undefined);
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!data) return;
    await api.saveSettings({ chat_history_enabled: Boolean(data.chat_history_enabled) });
    setSaved("Mentve.");
  }

  if (!data) return <div>Betöltés…</div>;

  return (
    <div>
      <div className="page-title">
        <div>
          <h2>Beállítások</h2>
          <p>A modell- és chunk beállítások az .env fájlból jönnek.</p>
        </div>
      </div>
      <form className="card form" onSubmit={save}>
        <label>
          <span>Chat history</span>
          <select
            value={String(data.chat_history_enabled)}
            onChange={(e) => setData({ ...data, chat_history_enabled: e.target.value === "true" })}
          >
            <option value="true">bekapcsolva</option>
            <option value="false">kikapcsolva</option>
          </select>
        </label>
        <div className="muted">LLM: {String(data.llm_provider)} / {String(data.llm_model)}</div>
        <div className="muted">Embedding: {String(data.embedding_provider)} / {String(data.embedding_model)}</div>
        <div className="muted">CHUNK_SIZE={String(data.chunk_size)} · OVERLAP={String(data.chunk_overlap)} · TOP_K={String(data.top_k)}</div>
        <div className="muted">MAX_FILE_SIZE={String(data.max_file_size)} bájt</div>
        <button className="btn" type="submit">Mentés</button>
        {saved && <div className="success">{saved}</div>}
      </form>
    </div>
  );
}
