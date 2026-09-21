import logging
import time

from app.database import get_session_factory
from app.workers.processor import process_job
from app.workers.queue import claim_next_job

logger = logging.getLogger("local_ai_chatbot.worker")


def run_worker_forever(poll_seconds: float = 1.0) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("Document worker started")
    while True:
        db = get_session_factory()()
        try:
            job = claim_next_job(db)
            if job:
                logger.info("Processing job %s (%s)", job.id, job.job_type)
                try:
                    process_job(db, job)
                except Exception:
                    logger.exception("Job %s failed", job.id)
            else:
                time.sleep(poll_seconds)
        finally:
            db.close()


if __name__ == "__main__":
    run_worker_forever()
