from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine: Engine | None = None
SessionLocal: sessionmaker | None = None


def _configure_sqlite(db_engine: Engine) -> None:
    @event.listens_for(db_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def configure_engine(database_url: str | None = None) -> Engine:
    global engine, SessionLocal
    settings = get_settings()
    url = database_url or settings.database_url
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        raw = url.replace("sqlite:///", "", 1)
        path = Path(raw)
        if not path.is_absolute():
            path = settings.sqlite_db_file
        path.parent.mkdir(parents=True, exist_ok=True)
        url = "sqlite:///" + path.as_posix()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, future=True, pool_pre_ping=True)
    if url.startswith("sqlite"):
        _configure_sqlite(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine


def get_engine() -> Engine:
    global engine
    if engine is None:
        configure_engine()
    assert engine is not None
    return engine


def get_session_factory() -> sessionmaker:
    global SessionLocal
    if SessionLocal is None:
        configure_engine()
    assert SessionLocal is not None
    return SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
