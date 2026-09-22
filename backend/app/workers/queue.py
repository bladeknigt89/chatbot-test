import json
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Document, Job, utcnow


def enqueue_job(db: Session, job_type: str, payload: dict) -> Job:
    job = Job(job_type=job_type, payload=json.dumps(payload, ensure_ascii=False), status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def claim_next_job(db: Session) -> Job | None:
    job = (
        db.query(Job)
        .filter(Job.status == "queued")
        .order_by(Job.created_at.asc())
        .first()
    )
    if not job:
        return None
    job.status = "running"
    job.started_at = utcnow()
    job.attempts = (job.attempts or 0) + 1
    db.commit()
    db.refresh(job)
    return job


def requeue_stale_jobs(db: Session, *, older_than_minutes: int | None = 45) -> int:
    """Worker-újraindítás / OOM után a 'running' jobok visszakerülnek a sorba.

    older_than_minutes=None: minden running job (worker friss indulásakor).
    """
    query = db.query(Job).filter(Job.status == "running")
    if older_than_minutes is not None:
        cutoff = utcnow() - timedelta(minutes=max(5, older_than_minutes))
        query = query.filter(Job.started_at.isnot(None), Job.started_at < cutoff)
    stale = query.all()
    count = 0
    for job in stale:
        attempts = int(job.attempts or 0)
        if attempts >= 3:
            job.status = "failed"
            job.error = "A feldolgozás többszöri próbálkozás után megszakadt (valószínű memóriahiány)."
            job.finished_at = utcnow()
            try:
                payload = json.loads(job.payload or "{}")
                document_id = payload.get("document_id")
                if document_id and job.job_type == "PROCESS_DOCUMENT":
                    document = db.query(Document).filter(Document.id == document_id).first()
                    if document and document.status in {"UPLOADED", "PROCESSING"}:
                        document.status = "ERROR"
                        document.processing_stage = "error"
                        document.error_message = job.error
            except Exception:
                pass
        else:
            job.status = "queued"
            job.started_at = None
            job.error = None
        count += 1
    if count:
        db.commit()
    return count
