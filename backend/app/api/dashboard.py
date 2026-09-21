from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_current_admin
from app.models import Agent, ApiKey, AuditLog, Document
from app.schemas import DashboardOut

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardOut, summary="Irányítópult statisztika")
def dashboard(db: Session = Depends(get_db), auth: AuthContext = Depends(get_current_admin)):
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return DashboardOut(
        agent_count=db.query(func.count(Agent.id)).scalar() or 0,
        document_count=db.query(func.count(Document.id)).scalar() or 0,
        processing_document_count=db.query(func.count(Document.id))
        .filter(Document.status.in_(["UPLOADED", "PROCESSING"]))
        .scalar()
        or 0,
        api_key_count=db.query(func.count(ApiKey.id)).filter(ApiKey.status == "active").scalar() or 0,
        chat_requests_today=db.query(func.count(AuditLog.id))
        .filter(AuditLog.action == "CHAT_REQUEST", AuditLog.timestamp >= start)
        .scalar()
        or 0,
        errors_today=db.query(func.count(AuditLog.id))
        .filter(
            AuditLog.timestamp >= start,
            AuditLog.action.in_(["DOCUMENT_PROCESSING_FAILED", "ADMIN_LOGIN_FAILED"]),
        )
        .scalar()
        or 0,
    )
