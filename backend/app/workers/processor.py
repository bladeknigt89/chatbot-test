from __future__ import annotations

import gc
import logging

from sqlalchemy.orm import Session

from app.audit import write_audit
from app.config import get_settings
from app.documents.chunking import chunk_document
from app.documents.parsers import parse_document
from app.documents.storage import delete_file, resolve_document_path
from app.embeddings.factory import get_embedding_provider
from app.models import Agent, ChatMessage, ChatSession, Document, Job, utcnow
from app.rag.pipeline import RAGPipeline
from app.vectorstore.store import get_vector_store

logger = logging.getLogger("local_ai_chatbot.worker")

USER_PARSE_ERROR = "A dokumentum feldolgozása sikertelen. Ellenőrizze, hogy a fájl nem sérült-e."
USER_OCR_ERROR = (
    "A szkennelt PDF szövegének felismerése sikertelen. "
    "Ellenőrizze, hogy az OCR_ENABLED=true, és a RapidOCR vagy a Tesseract telepítve van."
)
USER_EMBED_ERROR = (
    "Az embedding készítése sikertelen. Ellenőrizze, hogy az Ollama fut-e, "
    "és a modell le van-e töltve (pl. ollama pull nomic-embed-text)."
)
USER_MEMORY_ERROR = (
    "A dokumentum feldolgozása memóriahiány miatt megszakadt. "
    "Próbálja újra, vagy kisebb fájlokkal / alacsonyabb OCR_DPI értékkel."
)


def process_job(db: Session, job: Job) -> None:
    payload = __import__("json").loads(job.payload)
    try:
        if job.job_type == "PROCESS_DOCUMENT":
            _process_document(db, payload["document_id"], reprocess=payload.get("reprocess", False))
        elif job.job_type == "DELETE_DOCUMENT":
            _delete_document(db, payload["document_id"], payload["agent_id"], payload.get("stored_filename"))
        elif job.job_type == "DELETE_AGENT":
            _delete_agent(db, payload["agent_id"])
        else:
            raise ValueError(f"Ismeretlen job típus: {job.job_type}")
        job.status = "done"
        job.finished_at = utcnow()
        job.error = None
        db.commit()
    except Exception as exc:
        logger.exception("Job failed: %s", job.id)
        job.status = "failed"
        job.error = str(exc)
        job.finished_at = utcnow()
        db.commit()
        raise
    finally:
        gc.collect()


def _set_progress(db: Session, document: Document, *, stage: str, percent: int) -> None:
    document.processing_stage = stage
    document.progress_percent = max(0, min(100, int(percent)))
    document.updated_at = utcnow()
    db.commit()


def _process_document(db: Session, document_id: str, reprocess: bool = False) -> None:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return
    settings = get_settings()
    document.status = "PROCESSING"
    document.error_message = None
    document.chunk_count = 0
    _set_progress(db, document, stage="parsing", percent=5)
    write_audit(
        db,
        user="worker",
        action="DOCUMENT_PROCESSING_STARTED",
        resource_type="document",
        resource_id=document.id,
        details=document.original_filename,
    )
    extracted = None
    chunks = None
    try:
        path = resolve_document_path(document.agent_id, document.stored_filename)
        _set_progress(db, document, stage="parsing", percent=8)

        def on_parse_progress(done: int, total: int) -> None:
            if total <= 0:
                return
            # Parse sáv: 8% → 24%
            percent = 8 + int(16 * min(done, total) / total)
            document.processing_stage = "parsing"
            document.progress_percent = percent
            document.updated_at = utcnow()
            db.commit()

        extracted = parse_document(path, document.mime_type, on_progress=on_parse_progress)
        _set_progress(db, document, stage="chunking", percent=25)
        chunks = chunk_document(extracted, settings.chunk_size, settings.chunk_overlap)
        # A teljes szöveg már nem kell a memóriában
        extracted = None
        if not chunks:
            raise ValueError("A dokumentumból nem jött létre feldolgozható szöveg.")
        _set_progress(db, document, stage="chunking", percent=35)
        store = get_vector_store()
        if reprocess:
            store.delete_document(document.agent_id, document.id)
        _set_progress(db, document, stage="embedding", percent=38)

        def on_embed_progress(percent: int, _done: int, _total: int) -> None:
            document.processing_stage = "embedding"
            document.progress_percent = percent
            document.updated_at = utcnow()
            db.commit()

        pipeline = RAGPipeline(get_embedding_provider(), None, store)  # type: ignore[arg-type]
        count = pipeline.index_chunks(
            agent_id=document.agent_id,
            document_id=document.id,
            document_name=document.original_filename,
            chunks=chunks,
            on_progress=on_embed_progress,
            batch_size=4,
        )
        chunks = None
        document.status = "READY"
        document.chunk_count = count
        document.error_message = None
        _set_progress(db, document, stage="ready", percent=100)
        write_audit(
            db,
            user="worker",
            action="DOCUMENT_PROCESSING_COMPLETED",
            resource_type="document",
            resource_id=document.id,
            details=f"chunks={count}",
        )
    except MemoryError as exc:
        logger.exception("Document processing OOM: %s", document_id)
        document.status = "ERROR"
        document.processing_stage = "error"
        document.error_message = USER_MEMORY_ERROR
        db.commit()
        write_audit(
            db,
            user="worker",
            action="DOCUMENT_PROCESSING_FAILED",
            resource_type="document",
            resource_id=document.id,
            details=document.error_message,
        )
        raise exc
    except Exception as exc:
        logger.exception("Document processing failed: %s", document_id)
        document.status = "ERROR"
        document.processing_stage = "error"
        document.error_message = _friendly_error(exc)
        db.commit()
        write_audit(
            db,
            user="worker",
            action="DOCUMENT_PROCESSING_FAILED",
            resource_type="document",
            resource_id=document.id,
            details=document.error_message,
        )
        raise
    finally:
        extracted = None
        chunks = None
        gc.collect()


def _friendly_error(exc: Exception) -> str:
    message = str(exc).strip()
    text = f"{type(exc).__name__} {exc}".lower()
    if isinstance(exc, MemoryError) or "memory" in text:
        return USER_MEMORY_ERROR
    if any(token in text for token in ["ocr", "szkennelt", "tesseract", "rapidocr"]):
        return message or USER_OCR_ERROR
    if message.startswith("A PDF-ből nem sikerült"):
        return message
    if any(
        token in text
        for token in [
            "embed",
            "ollama",
            "connect",
            "connection",
            "10061",
            "11434",
            "httpx",
            "not found",
            "pull",
            "model",
        ]
    ):
        message = str(exc).strip()
        if "ollama pull" in message.lower() or "embedding modell hiányzik" in message.lower():
            return message
        return USER_EMBED_ERROR
    return USER_PARSE_ERROR


def _delete_document(db: Session, document_id: str, agent_id: str, stored_filename: str | None) -> None:
    store = get_vector_store()
    store.delete_document(agent_id, document_id)
    from app.rag.memory import get_retrieval_memory

    get_retrieval_memory().delete_document(agent_id, document_id)
    if stored_filename:
        try:
            delete_file(agent_id, stored_filename)
        except OSError:
            logger.warning("Could not delete file %s/%s", agent_id, stored_filename)
    document = db.query(Document).filter(Document.id == document_id).first()
    if document:
        db.delete(document)
        db.commit()


def _delete_agent(db: Session, agent_id: str) -> None:
    store = get_vector_store()
    store.delete_agent(agent_id)
    from app.rag.memory import get_retrieval_memory

    get_retrieval_memory().delete_agent(agent_id)
    documents = db.query(Document).filter(Document.agent_id == agent_id).all()
    for document in documents:
        try:
            delete_file(agent_id, document.stored_filename)
        except OSError:
            logger.warning("Could not delete file for document %s", document.id)
        db.delete(document)
    db.query(ChatMessage).filter(ChatMessage.agent_id == agent_id).delete()
    db.query(ChatSession).filter(ChatSession.agent_id == agent_id).delete()
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent:
        db.delete(agent)
    db.commit()
