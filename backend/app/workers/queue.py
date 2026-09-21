import json

from sqlalchemy.orm import Session

from app.models import Job, utcnow


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
