from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.orm import Session
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app import __version__
from app.api import agents, auth, chat, dashboard, documents, keys, logs, widget
from app.api import settings as settings_api
from app.bootstrap import create_schema, ensure_directories, seed_admin, seed_settings
from app.config import get_settings
from app.database import configure_engine, get_session_factory
from app.logging_utils import setup_logging
from app.rate_limit import limiter

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = ROOT / "frontend" / "dist"
WIDGET_FILE = ROOT / "chat-widget" / "chat-widget.js"
CHAT_DEMO_FILE = ROOT / "chat-widget" / "chat-demo.html"


class SecurityHeadersMiddleware:
    """Pure ASGI middleware — nem puffereli a StreamingResponse törzsét."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "SAMEORIGIN"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                headers["X-XSS-Protection"] = "1; mode=block"
                if path.startswith("/api/"):
                    headers.setdefault("Cache-Control", "no-store")
            await send(message)

        await self.app(scope, receive, send_wrapper)

def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_dir)
    ensure_directories(settings)
    configure_engine(settings.database_url)
    create_schema()
    db: Session = get_session_factory()()
    try:
        seed_admin(db, settings)
        seed_settings(db, settings)
    finally:
        db.close()

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Lokális, dokumentumalapú multi-agent RAG chatbot platform.\n\n"
            "Hitelesítés:\n"
            "- Admin: `POST /api/auth/login` (httpOnly cookie) vagy Bearer JWT\n"
            "- Külső API: `Authorization: Bearer <API_KEY>`\n\n"
            "A widget a `/chat-widget.js` címen érhető el."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        swagger_ui_parameters={"persistAuthorization": True},
    )
    limiter.enabled = settings.app_env != "test"
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        expose_headers=["*"],
    )

    application.include_router(auth.router, prefix="/api")
    application.include_router(agents.router, prefix="/api")
    application.include_router(documents.router, prefix="/api")
    application.include_router(chat.router, prefix="/api")
    application.include_router(keys.router, prefix="/api")
    application.include_router(logs.router, prefix="/api")
    application.include_router(dashboard.router, prefix="/api")
    application.include_router(settings_api.router, prefix="/api")
    application.include_router(widget.router, prefix="/api")

    @application.get("/api/health", tags=["Health"], summary="Rendszerállapot")
    def health():
        return {
            "ok": True,
            "app": settings.app_name,
            "env": settings.app_env,
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
        }

    @application.get("/chat-widget.js", include_in_schema=False)
    def chat_widget_js():
        if WIDGET_FILE.exists():
            return FileResponse(WIDGET_FILE, media_type="application/javascript")
        return JSONResponse(status_code=404, content={"detail": "Widget nem található."})

    @application.get("/chat-demo.html", include_in_schema=False)
    def chat_demo_page():
        # Preferáld a chat-widget másolatot; fallback a frontend public/dist.
        for candidate in (
            CHAT_DEMO_FILE,
            FRONTEND_DIST / "chat-demo.html",
            ROOT / "frontend" / "public" / "chat-demo.html",
        ):
            if candidate.exists():
                return FileResponse(candidate, media_type="text/html; charset=utf-8")
        return JSONResponse(status_code=404, content={"detail": "Chat demó nem található."})

    if FRONTEND_DIST.exists():
        assets = FRONTEND_DIST / "assets"
        if assets.exists():
            application.mount("/assets", StaticFiles(directory=assets), name="assets")

        @application.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse(status_code=404, content={"detail": "Not found"})
            file_path = FRONTEND_DIST / full_path
            if full_path and file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            index = FRONTEND_DIST / "index.html"
            if index.exists():
                return FileResponse(index)
            return JSONResponse(status_code=404, content={"detail": "Frontend nincs buildelve."})
    else:

        @application.get("/", include_in_schema=False)
        def root_redirect():
            return RedirectResponse(url="/api/docs")

    def custom_openapi():
        if application.openapi_schema:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})
        schema["components"]["securitySchemes"]["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key or JWT",
            "description": "API kulcs (`lac_...`) vagy admin JWT.",
        }
        schema["components"]["securitySchemes"]["CookieAuth"] = {
            "type": "apiKey",
            "in": "cookie",
            "name": "lac_session",
        }
        schema["security"] = [{"BearerAuth": []}, {"CookieAuth": []}]
        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi
    return application
