import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../services/api";

const links = [
  ["/dashboard", "Irányítópult"],
  ["/agents", "Agentek"],
  ["/documents", "Dokumentumok"],
  ["/api-keys", "API kulcsok"],
  ["/logs", "Naplók"],
  ["/settings", "Beállítások"],
  ["/profile", "Profil"]
];

export default function Layout({ onLogout }: { onLogout: () => void }) {
  const navigate = useNavigate();

  async function logout() {
    await api.logout();
    onLogout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <h1>Helyi RAG</h1>
          <p>Dokumentumalapú chatbot</p>
        </div>
        <nav className="nav">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : "")}>
              {label}
            </NavLink>
          ))}
        </nav>
        <button onClick={logout}>Kijelentkezés</button>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
