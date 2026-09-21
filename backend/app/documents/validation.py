from dataclasses import dataclass

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls"}

MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
}

FRIENDLY_TYPE_ERROR = "Csak PDF, DOCX, XLSX vagy XLS fájl tölthető fel."
FRIENDLY_SIZE_ERROR = "A fájl mérete meghaladja a megengedett limitet."
FRIENDLY_NAME_ERROR = "Érvénytelen fájlnév."
FRIENDLY_CONTENT_ERROR = "A fájl tartalma nem egyezik a kiterjesztéssel, vagy sérült."


@dataclass
class ValidatedUpload:
    extension: str
    mime_type: str
    filename: str


def _safe_filename(name: str) -> str:
    cleaned = name.replace("\\", "/").split("/")[-1].strip()
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError(FRIENDLY_NAME_ERROR)
    if "\x00" in cleaned:
        raise ValueError(FRIENDLY_NAME_ERROR)
    return cleaned


def detect_extension_from_bytes(data: bytes, filename: str) -> str:
    name = _safe_filename(filename)
    ext = ""
    if "." in name:
        ext = "." + name.rsplit(".", 1)[-1].lower()
    if len(data) >= 5 and data[:5] == b"%PDF-":
        return ".pdf"
    if len(data) >= 8 and data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        if ext == ".xls":
            return ".xls"
        raise ValueError(FRIENDLY_CONTENT_ERROR)
    if len(data) >= 4 and data[:2] == b"PK":
        lowered = data[:8000].lower()
        if b"word/" in lowered or b"word\\" in lowered:
            return ".docx"
        if b"xl/" in lowered or b"xl\\" in lowered:
            return ".xlsx"
        if ext in {".docx", ".xlsx"}:
            return ext
        raise ValueError(FRIENDLY_CONTENT_ERROR)
    if ext in ALLOWED_EXTENSIONS:
        raise ValueError(FRIENDLY_CONTENT_ERROR)
    raise ValueError(FRIENDLY_TYPE_ERROR)


def validate_upload(filename: str, data: bytes, max_size: int) -> ValidatedUpload:
    name = _safe_filename(filename)
    if len(data) == 0:
        raise ValueError("A fájl üres.")
    if len(data) > max_size:
        raise ValueError(FRIENDLY_SIZE_ERROR)
    extension = detect_extension_from_bytes(data, name)
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(FRIENDLY_TYPE_ERROR)
    declared = ""
    if "." in name:
        declared = "." + name.rsplit(".", 1)[-1].lower()
    if declared and declared != extension:
        raise ValueError(FRIENDLY_CONTENT_ERROR)
    return ValidatedUpload(
        extension=extension,
        mime_type=MIME_BY_EXT[extension],
        filename=name,
    )
