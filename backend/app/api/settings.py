from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import AuthContext, get_current_admin
from app.models import SystemSetting
from app.schemas import SettingsOut, SettingsUpdate

router = APIRouter(tags=["Settings"])


@router.get("/settings", response_model=SettingsOut, summary="Rendszerbeállítások")
def get_settings_api(db: Session = Depends(get_db), auth: AuthContext = Depends(get_current_admin)):
    settings = get_settings()
    row = db.query(SystemSetting).filter(SystemSetting.key == "CHAT_HISTORY_ENABLED").first()
    chat_history = settings.chat_history_enabled
    if row:
        chat_history = row.value.lower() in {"1", "true", "yes", "on"}
    return SettingsOut(
        chat_history_enabled=chat_history,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        top_k=settings.top_k,
        max_file_size=settings.max_file_size,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        embedding_provider=settings.embedding_provider,
        embedding_model=settings.embedding_model,
        ocr_enabled=settings.ocr_enabled,
    )


@router.put("/settings", response_model=SettingsOut, summary="Beállítások mentése")
def update_settings(
    payload: SettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_current_admin),
):
    if payload.chat_history_enabled is not None:
        value = "true" if payload.chat_history_enabled else "false"
        row = db.query(SystemSetting).filter(SystemSetting.key == "CHAT_HISTORY_ENABLED").first()
        if row:
            row.value = value
        else:
            db.add(SystemSetting(key="CHAT_HISTORY_ENABLED", value=value))
        db.commit()
    return get_settings_api(db=db, auth=auth)
