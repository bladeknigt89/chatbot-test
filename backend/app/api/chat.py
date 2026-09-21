import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.bootstrap import get_setting_bool
from app.config import get_settings
from app.database import get_db, get_session_factory
from app.deps import AuthContext, get_auth_context
from app.embeddings.factory import get_embedding_provider
from app.llm.factory import get_llm_provider
from app.models import Agent, ChatMessage, ChatSession
from app.rag.pipeline import RAGPipeline
from app.rag.prompts import build_messages, no_info_reply
from app.rate_limit import limiter
from app.schemas import ChatRequest, ChatResponse, ChatSource
from app.vectorstore.store import get_vector_store

logger = logging.getLogger("local_ai_chatbot.chat")
router = APIRouter(tags=["Chat"])


def _pipeline() -> RAGPipeline:
    return RAGPipeline(get_embedding_provider(), get_llm_provider(), get_vector_store())


def _active_agent(db: Session, agent_id: str) -> Agent:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Az agent nem található.")
    if agent.status != "active":
        raise HTTPException(status_code=403, detail="Az agent jelenleg inaktív.")
    return agent


def _session(db: Session, agent_id: str, session_id: str | None) -> ChatSession:
    if session_id:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.agent_id == agent_id)
            .first()
        )
        if session:
            return session
    session = ChatSession(agent_id=agent_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _maybe_store(
    db: Session,
    *,
    session_id: str,
    agent_id: str,
    user_message: str,
    assistant_message: str,
    sources: list[ChatSource],
) -> None:
    settings = get_settings()
    if not get_setting_bool(db, "CHAT_HISTORY_ENABLED", settings.chat_history_enabled):
        return
    db.add(
        ChatMessage(
            session_id=session_id,
            agent_id=agent_id,
            role="user",
            content=user_message,
        )
    )
    db.add(
        ChatMessage(
            session_id=session_id,
            agent_id=agent_id,
            role="assistant",
            content=assistant_message,
            sources_json=json.dumps([item.model_dump() for item in sources], ensure_ascii=False),
        )
    )
    db.commit()


@router.post(
    "/chat/{agent_id}",
    response_model=ChatResponse,
    summary="Chat kérés agenthez",
)
@limiter.limit(get_settings().chat_rate_limit)
def chat(
    agent_id: str,
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    agent = _active_agent(db, agent_id)
    session = _session(db, agent.id, payload.session_id)
    # Skalárok a stream előtt — a request DB session a válasz előtt lezáródik.
    agent_pk = agent.id
    agent_prompt = agent.system_prompt or ""
    session_pk = session.id
    question = payload.message
    include_sources = payload.include_sources

    write_audit(
        db,
        user=auth.actor,
        action="CHAT_REQUEST",
        resource_type="agent",
        resource_id=agent_pk,
        details="message_length=%s" % len(question),
        request=request,
    )
    pipeline = _pipeline()
    if payload.stream:

        def event_stream() -> Iterator[bytes]:
            try:
                chunks: list[str] = []
                matches = pipeline.retrieve(agent_id=agent_pk, question=question)
                sources = pipeline._sources(matches) if include_sources else []
                if not matches:
                    answer = no_info_reply(question)
                    chunks.append(answer)
                    yield _sse_bytes("token", {"text": answer})
                else:
                    context = pipeline.build_context(matches)
                    messages = build_messages(
                        question=question,
                        context=context,
                        agent_system_prompt=agent_prompt,
                        has_context=True,
                    )
                    for token in pipeline._llm().stream(messages, get_settings().llm_temperature):
                        chunks.append(token)
                        yield _sse_bytes("token", {"text": token})
                answer = "".join(chunks).strip()
                store_db = get_session_factory()()
                try:
                    _maybe_store(
                        store_db,
                        session_id=session_pk,
                        agent_id=agent_pk,
                        user_message=question,
                        assistant_message=answer,
                        sources=sources,
                    )
                finally:
                    store_db.close()
                yield _sse_bytes("sources", [item.model_dump() for item in sources])
                yield _sse_bytes("done", {"session_id": session_pk, "message": answer})
            except Exception as exc:
                logger.exception("Chat stream failed")
                yield _sse_bytes("error", {"detail": str(exc) or "A válasz generálása sikertelen."})
                yield _sse_bytes(
                    "done",
                    {
                        "session_id": session_pk,
                        "message": "Hiba történt a válasz generálása közben.",
                    },
                )

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    result = pipeline.answer(
        agent_id=agent_pk,
        question=question,
        agent_system_prompt=agent_prompt,
        include_sources=include_sources,
    )
    _maybe_store(
        db,
        session_id=session_pk,
        agent_id=agent_pk,
        user_message=question,
        assistant_message=result.answer,
        sources=result.sources,
    )
    return ChatResponse(session_id=session_pk, message=result.answer, sources=result.sources)


def _sse_bytes(event: str, data) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
