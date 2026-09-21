from dataclasses import dataclass

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey, User, utcnow
from app.security import COOKIE_NAME, decode_access_token, hash_api_key, looks_like_api_key


@dataclass
class AuthContext:
    kind: str
    username: str
    api_key_id: str | None = None

    @property
    def actor(self) -> str:
        if self.kind == "api_key" and self.api_key_id:
            return f"api_key:{self.username}"
        return self.username

    @property
    def is_admin(self) -> bool:
        return self.kind == "admin"


def _unauthorized(detail: str = "Hitelesítés szükséges.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def get_current_admin(
    request: Request,
    db: Session = Depends(get_db),
    lac_session: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> AuthContext:
    token = lac_session
    if not token:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            candidate = auth[7:].strip()
            if not looks_like_api_key(candidate):
                token = candidate
    if not token:
        raise _unauthorized()
    payload = decode_access_token(token)
    if not payload or payload.get("typ") != "admin":
        raise _unauthorized("Érvénytelen vagy lejárt munkamenet.")
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise _unauthorized("A felhasználó nem található.")
    return AuthContext(kind="admin", username=user.username)


def get_auth_context(
    request: Request,
    db: Session = Depends(get_db),
    lac_session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    authorization: str | None = Header(default=None),
) -> AuthContext:
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
        if looks_like_api_key(raw):
            key_hash = hash_api_key(raw)
            api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
            if not api_key:
                raise _unauthorized("Érvénytelen API kulcs.")
            if api_key.status != "active":
                raise HTTPException(status_code=403, detail="Az API kulcs vissza lett vonva.")
            api_key.last_used_at = utcnow()
            db.commit()
            return AuthContext(kind="api_key", username=api_key.key_prefix, api_key_id=api_key.id)
        payload = decode_access_token(raw)
        if payload and payload.get("typ") == "admin":
            username = payload.get("sub")
            user = db.query(User).filter(User.username == username).first()
            if user:
                return AuthContext(kind="admin", username=user.username)

    if lac_session:
        payload = decode_access_token(lac_session)
        if payload and payload.get("typ") == "admin":
            username = payload.get("sub")
            user = db.query(User).filter(User.username == username).first()
            if user:
                return AuthContext(kind="admin", username=user.username)

    raise _unauthorized()
