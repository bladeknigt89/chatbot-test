import { FormEvent, useState } from "react";
import { api } from "../services/api";

export default function Profile() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function save(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await api.changePassword(current, next);
      setMessage("A jelszó megváltozott.");
      setCurrent("");
      setNext("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nem sikerült a mentés.");
    }
  }

  return (
    <div>
      <div className="page-title">
        <div>
          <h2>Profil</h2>
          <p>Az alapértelmezett admin jelszót az első belépés után cserélje le.</p>
        </div>
      </div>
      <form className="card form" onSubmit={save}>
        <label>
          Jelenlegi jelszó
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </label>
        <label>
          Új jelszó
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} minLength={8} />
        </label>
        {error && <div className="error">{error}</div>}
        {message && <div className="success">{message}</div>}
        <button className="btn" type="submit">Jelszó mentése</button>
      </form>
    </div>
  );
}
