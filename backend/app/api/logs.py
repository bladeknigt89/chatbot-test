from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_current_admin
from app.models import AuditLog
from app.schemas import AuditLogOut

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
