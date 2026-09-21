export type Agent = {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  status: string;
  widget_primary_color: string;
  widget_title: string;
  widget_position: string;
  widget_welcome_message: string;
  created_at: string;
  updated_at: string;
  document_count: number;
};

export type DocumentItem = {
  id: string;
  agent_id: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  status: string;
  processing_stage: string;
  progress_percent: number;
  error_message: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
};

export type Dashboard = {
  agent_count: number;
  document_count: number;
  processing_document_count: number;
  api_key_count: number;
  chat_requests_today: number;
  errors_today: number;
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: "include",
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init.headers || {})
    }
  });
  if (response.status === 204) {
    return undefined as T;
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "A kérés sikertelen.");
  }
  return data as T;
}

export const api = {
  login: (username: string, password: string) =>
    request("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request<{ username: string }>("/api/auth/me"),
  changePassword: (current_password: string, new_password: string) =>
    request("/api/auth/password", { method: "PUT", body: JSON.stringify({ current_password, new_password }) }),
  dashboard: () => request<Dashboard>("/api/dashboard"),
  agents: () => request<Agent[]>("/api/agents"),
  agent: (id: string) => request<Agent>(`/api/agents/${id}`),
  createAgent: (payload: Partial<Agent>) =>
    request<Agent>("/api/agents", { method: "POST", body: JSON.stringify(payload) }),
  updateAgent: (id: string, payload: Partial<Agent>) =>
    request<Agent>(`/api/agents/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteAgent: (id: string) => request(`/api/agents/${id}`, { method: "DELETE" }),
  documents: () => request<DocumentItem[]>("/api/documents"),
  agentDocuments: (id: string) => request<DocumentItem[]>(`/api/agents/${id}/documents`),
  upload: (agentId: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<DocumentItem>(`/api/agents/${agentId}/documents`, { method: "POST", body });
  },
  deleteDocument: (agentId: string, documentId: string) =>
    request(`/api/agents/${agentId}/documents/${documentId}`, { method: "DELETE" }),
  reprocess: (agentId: string, documentId: string) =>
    request(`/api/agents/${agentId}/documents/${documentId}/reprocess`, { method: "POST" }),
  keys: () => request<Array<Record<string, string>>>("/api/keys"),
  createKey: (name: string) =>
    request<{ key: string; id: string; name: string; key_prefix: string }>("/api/keys", {
      method: "POST",
      body: JSON.stringify({ name })
    }),
  revokeKey: (id: string) => request(`/api/keys/${id}/revoke`, { method: "POST" }),
  deleteKey: (id: string) => request(`/api/keys/${id}`, { method: "DELETE" }),
  logs: (params: URLSearchParams) => request<Array<Record<string, string>>>(`/api/logs?${params}`),
  settings: () => request<Record<string, string | number | boolean>>("/api/settings"),
  saveSettings: (payload: Record<string, boolean>) =>
    request("/api/settings", { method: "PUT", body: JSON.stringify(payload) }),
  chat: (agentId: string, message: string, sessionId?: string) =>
    request<{ session_id: string; message: string; sources: Array<Record<string, string>> }>(
      `/api/chat/${agentId}`,
      { method: "POST", body: JSON.stringify({ message, session_id: sessionId, stream: false }) }
    )
};
