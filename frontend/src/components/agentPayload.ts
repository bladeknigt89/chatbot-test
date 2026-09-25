import { Agent } from "../services/api";
import { chatLogPayload } from "./ChatLogToggles";

/** Csak a szerkeszthető agent mezők — ne küldjük az id/document_count mezőket. */
export function agentSettingsPayload(agent: Agent): Partial<Agent> {
  return {
    name: agent.name,
    description: agent.description,
    system_prompt: agent.system_prompt,
    status: agent.status,
    show_sources: agent.show_sources !== false,
    knowledge_profile: agent.knowledge_profile || "auto",
    ...chatLogPayload(agent),
    widget_primary_color: agent.widget_primary_color,
    widget_title: agent.widget_title,
    widget_position: agent.widget_position,
    widget_welcome_message: agent.widget_welcome_message,
  };
}
