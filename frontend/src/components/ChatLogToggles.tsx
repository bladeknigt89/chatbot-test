import { Agent } from "../services/api";

type ChatLogKey =
  | "chat_log_enabled"
  | "chat_log_token"
  | "chat_log_ip"
  | "chat_log_client"
  | "chat_log_agent"
  | "chat_log_question"
  | "chat_log_answer";

type Props = {
  agent: Agent;
  onChange: (next: Agent | ((prev: Agent) => Agent)) => void;
};

const FIELDS: Array<{ key: ChatLogKey; label: string }> = [
  { key: "chat_log_enabled", label: "Chat napló bekapcsolva" },
  { key: "chat_log_token", label: "Token / auth (prefix + API kulcs neve, soha nem a teljes kulcs)" },
  { key: "chat_log_ip", label: "IP cím" },
  { key: "chat_log_client", label: "Kliens (User-Agent)" },
  { key: "chat_log_agent", label: "Agent neve" },
  { key: "chat_log_question", label: "Feltett kérdés" },
  { key: "chat_log_answer", label: "AI válasz" },
];

/** Tiszta állapotátmenet — unit tesztekhez és a komponenshez. */
export function applyChatLogToggle(agent: Agent, key: ChatLogKey, value: boolean): Agent {
  return { ...agent, [key]: value };
}

export default function ChatLogToggles({ agent, onChange }: Props) {
  const enabled = Boolean(agent.chat_log_enabled);
  return (
    <div style={{ display: "grid", gap: 8 }}>
      <p className="muted" style={{ margin: 0 }}>
        A chat üzenetek külön naplóba kerülnek (nem az auditba). Alapból kikapcsolva.
      </p>
      {FIELDS.map(({ key, label }) => {
        const isMaster = key === "chat_log_enabled";
        const checked = Boolean(agent[key]);
        return (
          <label key={key} className="checkbox-row">
            <input
              type="checkbox"
              checked={checked}
              disabled={!isMaster && !enabled}
              onChange={(e) => {
                const value = e.target.checked;
                onChange((prev) => applyChatLogToggle(prev, key, value));
              }}
            />
            <span>{label}</span>
          </label>
        );
      })}
    </div>
  );
}

export function chatLogPayload(agent: Agent) {
  return {
    chat_log_enabled: Boolean(agent.chat_log_enabled),
    chat_log_token: agent.chat_log_token !== false,
    chat_log_ip: agent.chat_log_ip !== false,
    chat_log_client: agent.chat_log_client !== false,
    chat_log_agent: agent.chat_log_agent !== false,
    chat_log_question: agent.chat_log_question !== false,
    chat_log_answer: agent.chat_log_answer !== false,
  };
}
