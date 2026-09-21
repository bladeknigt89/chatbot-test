import { FormEvent, useEffect, useState } from "react";
import { api } from "../services/api";

type KeyRow = {
  id: string;
  name: string;
  key_prefix: string;
  status: string;
  created_at: string;
};

export default function ApiKeys() {
  const [keys, setKeys] = useState<KeyRow[]>([]);
  const [name, setName] = useState("widget");
  const [secret, setSecret] = useState("");

  async function load() {
    setKeys((await api.keys()) as unknown as KeyRow[]);
  }

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    const created = await api.createKey(name);
    setSecret(created.key);
    await load();
  }

  return (
    <div>
      <div className="page-title">
        <div>
          <h2>API kulcsok</h2>
          <p>A teljes kulcsot csak egyszer mutatjuk meg.</p>
        </div>
      </div>
      <form className="card form" onSubmit={create} style={{ marginBottom: 16 }}>
        <label>
          Név
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <button className="btn" type="submit">Kulcs létrehozása</button>
        {secret && (
          <div>
            <div className="success">Másolja el most, később nem lesz látható:</div>
            <pre className="code">{secret}</pre>
          </div>
        )}
      </form>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Név</th>
              <th>Prefix</th>
              <th>Státusz</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {keys.map((key) => (
              <tr key={key.id}>
                <td>{key.name}</td>
                <td>{key.key_prefix}</td>
                <td>{key.status}</td>
                <td className="row">
                  {key.status === "active" && (
                    <button className="btn ghost" onClick={() => api.revokeKey(key.id).then(load)}>
                      Visszavonás
                    </button>
                  )}
                  <button className="btn danger" onClick={() => api.deleteKey(key.id).then(load)}>
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
