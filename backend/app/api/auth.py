from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.config import get_settings
from app.database import get_db
from app.deps import AuthContext, get_current_admin
from app.models import User
from app.rate_limit import limiter
from app.schemas import LoginRequest, PasswordChangeRequest, UserOut
from app.security import COOKIE_NAME, create_access_token, hash_password, verify_password

router = APIRouter(tags=["Auth"])


@router.post(
    "/auth/login",
    summary="Admin bejelentkezés",
    responses={401: {"description": "Hibás belépési adatok"}},
)
@limiter.limit(get_settings().login_rate_limit)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        write_audit(
            db,
            user=payload.username,
            action="ADMIN_LOGIN_FAILED",
            resource_type="user",
            details="invalid credentials",
            request=request,
        )
        raise HTTPException(status_code=401, detail="Hibás felhasználónév vagy jelszó.")
    token = create_access_token(user.username)
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    write_audit(
        db,
        user=user.username,
        action="ADMIN_LOGIN",
        resource_type="user",
        resource_id=user.id,
        request=request,
    )
    return {"ok": True, "user": UserOut.model_validate(user)}


@router.post("/auth/logout", summary="Kijelentkezés")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/auth/me", response_model=UserOut, summary="Aktuális admin")
def me(auth: AuthContext = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == auth.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="A felhasználó nem található.")
    return user


@router.put("/auth/password", summary="Jelszó módosítása")
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    auth: AuthContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == auth.username).first()
    if not user or not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="A jelenlegi jelszó hibás.")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    write_audit(
        db,
        user=auth.username,
        action="ADMIN_PASSWORD_CHANGED",
        resource_type="user",
        resource_id=user.id,
        request=request,
    )
    return {"ok": True}
