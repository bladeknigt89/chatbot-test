import { Navigate, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Agents from "./pages/Agents";
import AgentDetail from "./pages/AgentDetail";
import Documents from "./pages/Documents";
import ApiKeys from "./pages/ApiKeys";
import Logs from "./pages/Logs";
import Settings from "./pages/Settings";
import Profile from "./pages/Profile";
import { api } from "./services/api";

export default function App() {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    api
      .me()
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false))
      .finally(() => setReady(true));
  }, []);

  if (!ready) {
    return <div className="content">Betöltés…</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<Login onLogin={() => setAuthed(true)} />} />
      <Route
        path="/"
        element={authed ? <Layout onLogout={() => setAuthed(false)} /> : <Navigate to="/login" replace />}
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="agents" element={<Agents />} />
        <Route path="agents/:id" element={<AgentDetail />} />
        <Route path="documents" element={<Documents />} />
        <Route path="api-keys" element={<ApiKeys />} />
        <Route path="logs" element={<Logs />} />
        <Route path="settings" element={<Settings />} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to={authed ? "/dashboard" : "/login"} replace />} />
    </Routes>
  );
}
