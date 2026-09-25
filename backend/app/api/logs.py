from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_current_admin
from app.models import AuditLog, ChatInteractionLog
from app.schemas import AuditLogOut, ChatInteractionLogOut

router = APIRouter(tags=["Audit logs"])


@router.get("/logs", response_model=list[AuditLogOut], summary="Audit napló")
def list_logs(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_admin),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
):
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if date_from:
        query = query.filter(AuditLog.timestamp >= date_from)
    if date_to:
        query = query.filter(AuditLog.timestamp <= date_to)
    return query.limit(limit).all()


@router.get(
    "/chat-logs",
    response_model=list[ChatInteractionLogOut],
    summary="Chat üzenetnapló",
)
def list_chat_logs(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_admin),
    agent_id: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
):
    query = db.query(ChatInteractionLog).order_by(ChatInteractionLog.timestamp.desc())
    if agent_id:
        query = query.filter(ChatInteractionLog.agent_id == agent_id)
    if date_from:
        query = query.filter(ChatInteractionLog.timestamp >= date_from)
    if date_to:
        query = query.filter(ChatInteractionLog.timestamp <= date_to)
    return query.limit(limit).all()
