from __future__ import annotations

import logging
import re
import shutil
import threading
from collections.abc import Callable
from pathlib import Path

from PIL import Image

from app.config import get_settings

logger = logging.getLogger("local_ai_chatbot.ocr")

MIN_TEXT_CHARS = 40
_TESSERACT_CANDIDATES = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    Path("/usr/bin/tesseract"),
    Path("/usr/local/bin/tesseract"),
)

_rapid_lock = threading.Lock()
_rapid_engine = None


def page_needs_ocr(text: str) -> bool:
    compact = re.sub(r"[^0-9A-Za-zÁÉÍÓÖŐÚÜŰáéíóöőúüű]", "", text or "")
    return len(compact) < MIN_TEXT_CHARS


class PdfOcrSession:
    """Egy PDF-megnyitás sok oldal OCR-jéhez — elkerüli a fájl százszori újratöltését."""

    def __init__(self, path: Path, dpi: int | None = None) -> None:
        self.path = Path(path)
        self.dpi = int(dpi or get_settings().ocr_dpi or 160)
        self._document = None

    def __enter__(self) -> PdfOcrSession:
        if not get_settings().ocr_enabled:
            return self
        try:
            import pypdfium2 as pdfium
        except ImportError:
            logger.warning("pypdfium2 hiányzik, a szkennelt PDF oldal nem rastizálható.")
            return self
        try:
            self._document = pdfium.PdfDocument(str(self.path))
        except Exception:
            logger.exception("PDF megnyitása OCR-hez sikertelen: %s", self.path.name)
            self._document = None
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        document = self._document
        self._document = None
        if document is None:
            return
        try:
            document.close()
        except Exception:
            logger.debug("PDF OCR session close failed", exc_info=True)

    def ocr_page(self, page_number: int) -> str:
        if not get_settings().ocr_enabled:
            return ""
        image = self._render_page(page_number)
        if image is None:
            return ""
        try:
            return _clean(_ocr_with_tesseract(image) or _ocr_with_rapidocr(image))
        finally:
            try:
                image.close()
            except Exception:
                pass

    def _render_page(self, page_number: int) -> Image.Image | None:
        document = self._document
        if document is None:
            return render_pdf_page(self.path, page_number, dpi=self.dpi)
        page = None
        bitmap = None
        try:
            index = page_number - 1
            if index < 0 or index >= len(document):
                return None
            page = document[index]
            scale = max(self.dpi, 72) / 72
            bitmap = page.render(scale=scale)
            to_pil = bitmap.to_pil
            image = to_pil() if callable(to_pil) else to_pil
            if image.mode != "RGB":
                converted = image.convert("RGB")
                try:
                    image.close()
                except Exception:
                    pass
                image = converted
            return image
        except Exception:
            logger.exception("PDF oldal rastizálása sikertelen: %s #%s", self.path.name, page_number)
            return None
        finally:
            if bitmap is not None:
                try:
                    close = getattr(bitmap, "close", None)
                    if callable(close):
                        close()
                except Exception:
                    pass
            if page is not None:
                try:
                    close = getattr(page, "close", None)
                    if callable(close):
                        close()
                except Exception:
                    pass


def ocr_pdf_page(path: Path, page_number: int) -> str:
    settings = get_settings()
    if not settings.ocr_enabled:
        return ""
    with PdfOcrSession(path, dpi=settings.ocr_dpi) as session:
        return session.ocr_page(page_number)


def render_pdf_page(path: Path, page_number: int, dpi: int = 160) -> Image.Image | None:
    try:
        import pypdfium2 as pdfium
    except ImportError:
        logger.warning("pypdfium2 hiányzik, a szkennelt PDF oldal nem rastizálható.")
        return None
    document = None
    page = None
    bitmap = None
    try:
        document = pdfium.PdfDocument(str(path))
        index = page_number - 1
        if index < 0 or index >= len(document):
            return None
        page = document[index]
        scale = max(int(dpi), 72) / 72
        bitmap = page.render(scale=scale)
        to_pil = bitmap.to_pil
        image = to_pil() if callable(to_pil) else to_pil
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image
    except Exception:
        logger.exception("PDF oldal rastizálása sikertelen: %s #%s", path.name, page_number)
        return None
    finally:
        if bitmap is not None:
            try:
                close = getattr(bitmap, "close", None)
                if callable(close):
                    close()
            except Exception:
                pass
        if page is not None:
            try:
                close = getattr(page, "close", None)
                if callable(close):
                    close()
            except Exception:
                pass
        if document is not None:
            try:
                document.close()
            except Exception:
                pass


def _tesseract_cmd() -> str | None:
    configured = (get_settings().tesseract_cmd or "").strip()
    if configured and Path(configured).exists():
        return configured
    found = shutil.which("tesseract")
    if found:
        return found
    for candidate in _TESSERACT_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return None


def _ocr_with_tesseract(image: Image.Image) -> str:
    cmd = _tesseract_cmd()
    if not cmd:
        return ""
    try:
        import pytesseract
    except ImportError:
        return ""
    pytesseract.pytesseract.tesseract_cmd = cmd
    languages = get_settings().ocr_languages or "hun+eng"
    for lang in (languages, "eng"):
        try:
            raw = pytesseract.image_to_string(image, lang=lang, config="--oem 1 --psm 6")
        except Exception as exc:
            logger.debug("Tesseract lang=%s sikertelen: %s", lang, exc)
            continue
        cleaned = _clean(raw)
        if cleaned:
            return cleaned
    return ""


def _ocr_with_rapidocr(image: Image.Image) -> str:
    engine = _get_rapid_engine()
    if engine is None:
        return ""
    result = None
    try:
        result = engine(image)
        lines = _rapid_lines(result)
        return _clean("\n".join(lines))
    except Exception:
        logger.exception("RapidOCR futása sikertelen")
        return ""
    finally:
        # A RapidOCROutput tartja a teljes képmátrixot — azonnal engedjük el.
        if result is not None:
            try:
                result.img = None
            except Exception:
                pass
            del result


def _get_rapid_engine():
    global _rapid_engine
    if _rapid_engine is not None:
        return _rapid_engine
    with _rapid_lock:
        if _rapid_engine is not None:
            return _rapid_engine
        try:
            from rapidocr import RapidOCR
        except ImportError:
            logger.warning("RapidOCR nincs telepítve, Tesseract nélküli OCR nem érhető el.")
            return None
        try:
            _rapid_engine = RapidOCR()
        except Exception:
            logger.exception("RapidOCR inicializálása sikertelen")
            return None
        return _rapid_engine


def _rapid_lines(result) -> list[str]:
    if result is None:
        return []
    txts = getattr(result, "txts", None)
    if txts:
        return [str(item).strip() for item in txts if str(item).strip()]
    if isinstance(result, (list, tuple)):
        rows = result[0] if result and isinstance(result[0], list) else result
        lines: list[str] = []
        for item in rows or []:
            if isinstance(item, str) and item.strip():
                lines.append(item.strip())
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                text = str(item[1]).strip()
                if text:
                    lines.append(text)
        return lines
    return []


def _clean(value: str) -> str:
    lines = [line.strip() for line in (value or "").replace("\x00", "").splitlines()]
    return "\n".join(line for line in lines if line)


ProgressCallback = Callable[[int, int], None]
