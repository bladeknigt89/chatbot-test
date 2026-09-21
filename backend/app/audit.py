
from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host
    return None


def write_audit(
    db: Session,
    *,
    user: str,
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    details: str = "",
    request: Request | None = None,
) -> None:
    log = AuditLog(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details[:4000],
        ip=client_ip(request),
    )
    db.add(log)
    db.commit()
