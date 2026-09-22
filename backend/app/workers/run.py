import gc
import logging
import time

from app.database import get_session_factory
from app.workers.processor import process_job
from app.workers.queue import claim_next_job, requeue_stale_jobs

logger = logging.getLogger("local_ai_chatbot.worker")


def run_worker_forever(poll_seconds: float = 1.0) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("Document worker started")
    db = get_session_factory()()
    try:
        recovered = requeue_stale_jobs(db, older_than_minutes=None)
        if recovered:
            logger.warning("Startup: requeued/failed %s interrupted job(s)", recovered)
    finally:
        db.close()
    last_requeue = time.monotonic()
    while True:
        db = get_session_factory()()
        try:
            now = time.monotonic()
            if now - last_requeue > 60:
                recovered = requeue_stale_jobs(db, older_than_minutes=45)
                if recovered:
                    logger.warning("Requeued/failed %s stale running job(s)", recovered)
                last_requeue = now
            job = claim_next_job(db)
            if job:
                logger.info("Processing job %s (%s)", job.id, job.job_type)
                try:
                    process_job(db, job)
                except Exception:
                    logger.exception("Job %s failed", job.id)
                finally:
                    gc.collect()
            else:
                time.sleep(poll_seconds)
        finally:
            db.close()


if __name__ == "__main__":
    run_worker_forever()
