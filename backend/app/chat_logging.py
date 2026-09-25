"""Agent-szintű chat interakció napló — külön a chat history-tól és az audittól."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from sqlalchemy.orm import Session

from app.audit import client_ip
from app.deps import AuthContext
from app.models import Agent, ApiKey, ChatInteractionLog


@dataclass(frozen=True)
class ChatLogPolicy:
    enabled: bool
    log_token: bool
    log_ip: bool
    log_client: bool
    log_agent: bool
    log_question: bool
    log_answer: bool
    agent_id: str
    agent_name: str

    @classmethod
    def from_agent(cls, agent: Agent) -> ChatLogPolicy:
        return cls(
            enabled=bool(getattr(agent, "chat_log_enabled", False)),
            log_token=bool(getattr(agent, "chat_log_token", True)),
            log_ip=bool(getattr(agent, "chat_log_ip", True)),
            log_client=bool(getattr(agent, "chat_log_client", True)),
            log_agent=bool(getattr(agent, "chat_log_agent", True)),
            log_question=bool(getattr(agent, "chat_log_question", True)),
            log_answer=bool(getattr(agent, "chat_log_answer", True)),
            agent_id=agent.id,
            agent_name=agent.name or "",
        )


def _token_label(auth: AuthContext) -> str:
    """Csak prefix / szerepkör — soha ne a teljes API kulcs."""
    if auth.kind == "api_key":
        return f"api_key:{auth.username}"
    return f"admin:{auth.username}"


def _api_key_name(db: Session, auth: AuthContext) -> str:
    if auth.kind != "api_key" or not auth.api_key_id:
        return ""
    row = db.query(ApiKey).filter(ApiKey.id == auth.api_key_id).first()
    return (row.name if row else "")[:200]


def _client_label(request: Request | None) -> str:
    if request is None:
        return ""
    ua = (request.headers.get("user-agent") or "").strip()
    return ua[:512]


def write_chat_interaction_log(
    db: Session,
    *,
    policy: ChatLogPolicy,
    auth: AuthContext,
    request: Request | None,
    session_id: str,
    question: str,
    answer: str,
) -> None:
    if not policy.enabled:
        return

    log_token = policy.log_token
    row = ChatInteractionLog(
        agent_id=policy.agent_id,
        session_id=session_id or "",
        auth_kind=auth.kind,
        token_label=_token_label(auth) if log_token else "",
        api_key_id=(auth.api_key_id or "") if log_token and auth.kind == "api_key" else "",
        api_key_name=_api_key_name(db, auth) if log_token else "",
        ip=client_ip(request) if policy.log_ip else None,
        client=_client_label(request) if policy.log_client else "",
        agent_name=policy.agent_name if policy.log_agent else "",
        question=(question or "")[:8000] if policy.log_question else "",
        answer=(answer or "")[:20000] if policy.log_answer else "",
    )
    db.add(row)
    db.commit()
