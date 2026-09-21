"""Backend API és dokumentum-worker indítása."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
RUN_DIR = ROOT / "storage" / "logs"
PID_FILE = ROOT / "storage" / "runtime.pids"


def python_bin() -> Path:
    if os.name == "nt":
        return BACKEND / ".venv" / "Scripts" / "python.exe"
    return BACKEND / ".venv" / "bin" / "python"


def require_python_314(py: Path) -> int | None:
    check = subprocess.run(
        [str(py), "-c", "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,14) else 1)"],
        check=False,
    )
    if check.returncode != 0:
        print("A virtuális környezet nem Python 3.14. Futtasd újra az install.bat / install.sh fájlt.")
        return 1
    return None


def main() -> int:
    sys.path.insert(0, str(BACKEND))
    from app.bootstrap import ensure_llm_ready
    from app.config import get_settings

    py = python_bin()
    if not py.exists():
        print("A virtuális környezet hiányzik. Futtasd az install.bat / install.sh fájlt.")
        return 1
    if (err := require_python_314(py)) is not None:
        return err

    get_settings.cache_clear()
    settings = get_settings()

    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        from install_ollama import ensure_ollama

        ensure_ollama(
            base_url=settings.llm_base_url,
            skip_install=True,
            models_json=ROOT / "models.json",
        )
    except Exception as exc:
        print(f"Ollama indítási ellenőrzés: {exc}")

    ensure_llm_ready(settings, pull=True)

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    api_log = open(RUN_DIR / "api.log", "a", encoding="utf-8")
    worker_log = open(RUN_DIR / "worker.log", "a", encoding="utf-8")

    api = subprocess.Popen(
        [
            str(py),
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            settings.app_host,
            "--port",
            str(settings.app_port),
        ],
        cwd=str(BACKEND),
        env=env,
        stdout=api_log,
        stderr=subprocess.STDOUT,
    )
    worker = subprocess.Popen(
        [str(py), "-m", "app.workers.run"],
        cwd=str(BACKEND),
        env=env,
        stdout=worker_log,
        stderr=subprocess.STDOUT,
    )
    PID_FILE.write_text(f"{api.pid}\n{worker.pid}\n", encoding="utf-8")
    url = settings.app_public_url.rstrip("/")
    print(f"Admin UI: {url}")
    print(f"Swagger:  {url}/api/docs")
    print(f"Widget:   {url}/chat-widget.js")
    print("Leállítás: Ctrl+C vagy stop.bat / stop.sh")

    def shutdown(*_args) -> None:
        for proc in (api, worker):
            if proc.poll() is None:
                proc.terminate()
        time.sleep(1)
        for proc in (api, worker):
            if proc.poll() is None:
                proc.kill()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    while True:
        if api.poll() is not None:
            print(f"A backend kilépett: {api.returncode}. Nézd a storage/logs/api.log fájlt.")
            shutdown()
        if worker.poll() is not None:
            print(f"A worker kilépett: {worker.returncode}. Nézd a storage/logs/worker.log fájlt.")
            shutdown()
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
