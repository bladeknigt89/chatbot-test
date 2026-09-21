from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.deps import AuthContext, get_current_admin
from app.models import ApiKey, utcnow
from app.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from app.security import generate_api_key, hash_api_key

router = APIRouter(tags=["API keys"])


@router.post(
    "/keys",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    summary="API kulcs létrehozása",
)
def create_key(
    payload: ApiKeyCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_admin),
):
    raw = generate_api_key()
    record = ApiKey(
        name=payload.name,
        key_hash=hash_api_key(raw),
        key_prefix=raw[:10],
        status="active",
        created_by=auth.username,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    write_audit(
        db,
        user=auth.actor,
        action="API_KEY_CREATED",
        resource_type="api_key",
        resource_id=record.id,
        details=f"prefix={record.key_prefix}",
        request=request,
    )
    return ApiKeyCreated(
        id=record.id,
        name=record.name,
        key_prefix=record.key_prefix,
        status=record.status,
        created_by=record.created_by,
        last_used_at=record.last_used_at,
        created_at=record.created_at,
        revoked_at=record.revoked_at,
        key=raw,
    )


@router.get("/keys", response_model=list[ApiKeyOut], summary="API kulcsok listája")
def list_keys(db: Session = Depends(get_db), auth: AuthContext = Depends(get_current_admin)):
    return db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()


@router.post("/keys/{key_id}/revoke", response_model=ApiKeyOut, summary="API kulcs visszavonása")
def revoke_key(
    key_id: str,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_admin),
):
    record = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Az API kulcs nem található.")
    record.status = "revoked"
    record.revoked_at = utcnow()
    db.commit()
    db.refresh(record)
    write_audit(
        db,
        user=auth.actor,
        action="API_KEY_REVOKED",
        resource_type="api_key",
        resource_id=record.id,
        details=f"prefix={record.key_prefix}",
        request=request,
    )
    return record


@router.delete("/keys/{key_id}", status_code=204, summary="API kulcs törlése")
def delete_key(
    key_id: str,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_admin),
):
    record = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Az API kulcs nem található.")
    write_audit(
        db,
        user=auth.actor,
        action="API_KEY_DELETED",
        resource_type="api_key",
        resource_id=record.id,
        details=f"prefix={record.key_prefix}",
        request=request,
    )
    db.delete(record)
    db.commit()
    return None
