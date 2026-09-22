import json

from app.models import Job, utcnow
from app.workers.queue import requeue_stale_jobs


def test_requeue_interrupted_jobs_on_startup(app_env, admin_client):
    from app.database import get_session_factory

    db = get_session_factory()()
    try:
        job = Job(
            job_type="PROCESS_DOCUMENT",
            payload=json.dumps({"document_id": "missing"}),
            status="running",
            started_at=utcnow(),
            attempts=1,
        )
        db.add(job)
        db.commit()
        job_id = job.id
        recovered = requeue_stale_jobs(db, older_than_minutes=None)
        assert recovered >= 1
        refreshed = db.query(Job).filter(Job.id == job_id).first()
        assert refreshed is not None
        assert refreshed.status == "queued"
        assert refreshed.started_at is None
    finally:
        db.close()
