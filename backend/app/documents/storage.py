from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.config import get_settings


@dataclass
class StoredFile:
    stored_filename: str
    relative_dir: str
    absolute_path: str


def stored_name(original_filename: str) -> str:
    suffix = ""
    if "." in original_filename:
        suffix = "." + original_filename.rsplit(".", 1)[-1].lower()
        if suffix not in {".pdf", ".docx", ".xlsx", ".xls"}:
            suffix = ""
    return f"{uuid4().hex}{suffix}"


def agent_storage_dir(agent_id: str):
    settings = get_settings()
    path = settings.storage_dir / agent_id
    path.mkdir(parents=True, exist_ok=True)
    resolved = path.resolve()
    storage_root = settings.storage_dir.resolve()
    if not str(resolved).startswith(str(storage_root)):
        raise ValueError("Érvénytelen tárolási útvonal.")
    return resolved


def save_bytes(agent_id: str, original_filename: str, data: bytes) -> StoredFile:
    name = stored_name(original_filename)
    directory = agent_storage_dir(agent_id)
    absolute = directory / name
    if not str(absolute.resolve()).startswith(str(directory)):
        raise ValueError("Érvénytelen fájlnév.")
    absolute.write_bytes(data)
    return StoredFile(
        stored_filename=name,
        relative_dir=agent_id,
        absolute_path=str(absolute),
    )


def resolve_document_path(agent_id: str, stored_filename: str):
    directory = agent_storage_dir(agent_id)
    candidate = (directory / stored_filename).resolve()
    if not str(candidate).startswith(str(directory)):
        raise ValueError("Érvénytelen fájlútvonal.")
    return candidate


def delete_file(agent_id: str, stored_filename: str) -> None:
    path = resolve_document_path(agent_id, stored_filename)
    if path.exists():
        path.unlink()
