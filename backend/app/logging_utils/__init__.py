from logging.config import dictConfig
from pathlib import Path


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                },
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(log_dir / "app.log"),
                    "encoding": "utf-8",
                    "formatter": "standard",
                },
            },
            "root": {"level": "INFO", "handlers": ["console", "file"]},
        }
    )
