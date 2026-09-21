import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

export default function Login({ onLogin }: { onLogin: () => void }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("ai");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.login(username, password);
      onLogin();
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Belépés sikertelen.");
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card form" onSubmit={onSubmit}>
        <h2>Admin belépés</h2>
        <p className="muted">Lokális chatbot felügyelet. Az alapértelmezett felhasználó az első telepítés után módosítható.</p>
        <label>
          Felhasználónév
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </label>
        <label>
          Jelszó
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        </label>
        {error && <div className="error">{error}</div>}
        <button className="btn" type="submit">Belépés</button>
      </form>
    </div>
  );
}
