from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.config import get_settings
from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.documents.storage import save_bytes
from app.documents.validation import validate_upload
from app.models import Agent, Document
from app.schemas import DocumentOut
from app.workers.queue import enqueue_job

router = APIRouter(tags=["Documents"])


def _agent_or_404(db: Session, agent_id: str) -> Agent:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Az agent nem található.")
    return agent


@router.post(
    "/agents/{agent_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Dokumentum feltöltése",
)
async def upload_document(
    agent_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    _agent_or_404(db, agent_id)
    settings = get_settings()
    data = await file.read()
    try:
        validated = validate_upload(file.filename or "document", data, settings.max_file_size)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    stored = save_bytes(agent_id, validated.filename, data)
    document = Document(
        agent_id=agent_id,
        original_filename=validated.filename,
        stored_filename=stored.stored_filename,
        mime_type=validated.mime_type,
        file_size=len(data),
        status="UPLOADED",
        processing_stage="uploaded",
        progress_percent=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    write_audit(
        db,
        user=auth.actor,
        action="DOCUMENT_UPLOADED",
        resource_type="document",
        resource_id=document.id,
        details=validated.filename,
        request=request,
    )
    enqueue_job(db, "PROCESS_DOCUMENT", {"document_id": document.id, "reprocess": False})
    return document


@router.get(
    "/agents/{agent_id}/documents",
    response_model=list[DocumentOut],
    summary="Agent dokumentumai",
)
def list_agent_documents(
    agent_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    _agent_or_404(db, agent_id)
    return (
        db.query(Document)
        .filter(Document.agent_id == agent_id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get("/documents", response_model=list[DocumentOut], summary="Minden dokumentum")
def list_all_documents(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    return db.query(Document).order_by(Document.created_at.desc()).all()


@router.delete(
    "/agents/{agent_id}/documents/{document_id}",
    status_code=202,
    summary="Dokumentum törlése",
)
def delete_document(
    agent_id: str,
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.agent_id == agent_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="A dokumentum nem található.")
    document.status = "DELETING"
    db.commit()
    write_audit(
        db,
        user=auth.actor,
        action="DOCUMENT_DELETED",
        resource_type="document",
        resource_id=document.id,
        details=document.original_filename,
        request=request,
    )
    enqueue_job(
        db,
        "DELETE_DOCUMENT",
        {
            "document_id": document.id,
            "agent_id": agent_id,
            "stored_filename": document.stored_filename,
        },
    )
    return {"ok": True, "status": "deleting"}


@router.post(
    "/agents/{agent_id}/documents/{document_id}/reprocess",
    response_model=DocumentOut,
    summary="Dokumentum újrafeldolgozása",
)
def reprocess_document(
    agent_id: str,
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.agent_id == agent_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="A dokumentum nem található.")
    document.status = "UPLOADED"
    document.processing_stage = "queued"
    document.progress_percent = 0
    document.error_message = None
    db.commit()
    write_audit(
        db,
        user=auth.actor,
        action="DOCUMENT_REPROCESSED",
        resource_type="document",
        resource_id=document.id,
        details=document.original_filename,
        request=request,
    )
    enqueue_job(db, "PROCESS_DOCUMENT", {"document_id": document.id, "reprocess": True})
    db.refresh(document)
    return document
