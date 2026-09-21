"""Ollama runtime telepítése, indítása és modellek letöltése (Windows / Linux).

A letöltendő modellek adatait a projektgyökér `models.json` fájljából olvassa.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "http://127.0.0.1:11434"
DEFAULT_MODELS_JSON = ROOT / "models.json"
WINDOWS_SETUP_URL = "https://ollama.com/download/OllamaSetup.exe"
LINUX_INSTALL_URL = "https://ollama.com/install.sh"

# Beépített fallback = a jelenlegi projekt default modelljei (ha a JSON hiányzik).
DEFAULT_MODELS_CONFIG: dict[str, Any] = {
    "base_url": DEFAULT_BASE,
    "llm": {
        "provider": "ollama",
        "model": "qwen2.5:7b",
        "temperature": 0.1,
    },
    "embedding": {
        "provider": "ollama",
        "model": "nomic-embed-text",
    },
    "models": [
        {
            "name": "qwen2.5:7b",
            "role": "llm",
            "description": "Helyi chat / RAG válaszadó modell",
        },
        {
            "name": "nomic-embed-text",
            "role": "embedding",
            "description": "Dokumentum-embedding modell",
        },
    ],
}


def load_models_config(path: Path | None = None) -> dict[str, Any]:
    """Modellek JSON betöltése; hiányzó fájlnál a beépített default."""
    config_path = path or DEFAULT_MODELS_JSON
    if not config_path.is_file():
        print(f"FIGYELEM: {config_path} nem található, beépített default modellek használata.")
        return json.loads(json.dumps(DEFAULT_MODELS_CONFIG))
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Érvénytelen models.json formátum: {config_path}")
    merged = json.loads(json.dumps(DEFAULT_MODELS_CONFIG))
    merged.update({k: v for k, v in data.items() if v is not None})
    if "llm" in data and isinstance(data["llm"], dict):
        merged["llm"] = {**DEFAULT_MODELS_CONFIG["llm"], **data["llm"]}
    if "embedding" in data and isinstance(data["embedding"], dict):
        merged["embedding"] = {**DEFAULT_MODELS_CONFIG["embedding"], **data["embedding"]}
    if not merged.get("models"):
        merged["models"] = list(DEFAULT_MODELS_CONFIG["models"])
    return merged


def model_names_to_pull(config: dict[str, Any]) -> list[str]:
    """Egyedi modellnevek a JSON-ból (models lista + llm/embedding)."""
    names: list[str] = []
    for item in config.get("models") or []:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]).strip())
    llm = (config.get("llm") or {}).get("model")
    emb = (config.get("embedding") or {}).get("model")
    for name in (llm, emb):
        if name and str(name).strip():
            names.append(str(name).strip())
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def which_ollama() -> str | None:
    found = shutil.which("ollama")
    if found:
        return found
    if os.name == "nt":
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Ollama" / "ollama.exe",
            Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
        ]
        for path in candidates:
            if path.is_file():
                return str(path)
    return None


def api_ready(base_url: str = DEFAULT_BASE, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=timeout) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def list_remote_models(base_url: str) -> list[str]:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [str(item.get("name", "")) for item in payload.get("models", []) if item.get("name")]
    except Exception:
        return []


def model_installed(installed: list[str], name: str) -> bool:
    short = name.split(":")[0]
    for item in installed:
        if item == name or item.startswith(f"{name}-") or item.startswith(f"{name}:"):
            return True
        if item.split(":")[0] == short:
            return True
    return False


def pull_model(name: str, *, ollama_bin: str | None = None, base_url: str = DEFAULT_BASE) -> None:
    """Modell letöltése `ollama pull`-lal (progress a terminálban)."""
    binary = ollama_bin or which_ollama()
    print(f"Modell letöltése: {name}")
    if binary:
        result = subprocess.run([binary, "pull", name], check=False)
        if result.returncode == 0:
            print(f"Modell kész: {name}")
            return
        print(f"FIGYELEM: az 'ollama pull {name}' kilépett ({result.returncode}), API próbálkozás...")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/pull",
        data=json.dumps({"name": name, "stream": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=3600) as response:
        last_status = ""
        while True:
            line = response.readline()
            if not line:
                break
            try:
                event = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            status = str(event.get("status") or "")
            if status and status != last_status:
                completed = event.get("completed")
                total = event.get("total")
                if completed is not None and total:
                    pct = int(completed * 100 / total)
                    print(f"  {name}: {status} ({pct}%)", flush=True)
                else:
                    print(f"  {name}: {status}", flush=True)
                last_status = status
            if event.get("error"):
                raise RuntimeError(f"Modell pull hiba ({name}): {event['error']}")
    print(f"Modell kész: {name}")


def ensure_models(
    config: dict[str, Any] | None = None,
    *,
    models_json: Path | None = None,
    skip_pull: bool = False,
) -> int:
    """Hiányzó modellek letöltése a models.json alapján."""
    cfg = config or load_models_config(models_json)
    base_url = str(cfg.get("base_url") or DEFAULT_BASE)
    names = model_names_to_pull(cfg)
    if not names:
        print("Nincs letöltendő modell a models.json-ban.")
        return 0
    if skip_pull:
        print(f"Modell letöltés kihagyva. Konfigurált: {', '.join(names)}")
        return 0
    if not api_ready(base_url):
        print(f"Az Ollama API nem elérhető ({base_url}), modellek nem tölthetők le.")
        return 1

    installed = list_remote_models(base_url)
    binary = which_ollama()
    failed = 0
    for name in names:
        if model_installed(installed, name):
            print(f"Modell már telepítve: {name}")
            continue
        try:
            pull_model(name, ollama_bin=binary, base_url=base_url)
            installed = list_remote_models(base_url)
        except Exception as exc:
            print(f"HIBA: {name} letöltése sikertelen: {exc}")
            failed += 1
    return 1 if failed else 0


def sync_env_from_models(config: dict[str, Any], env_path: Path | None = None) -> None:
    """A .env LLM/EMBEDDING mezőit a models.json-hoz igazítja."""
    path = env_path or (ROOT / ".env")
    if not path.is_file():
        example = ROOT / ".env.example"
        if example.is_file():
            path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            return

    llm = config.get("llm") or {}
    emb = config.get("embedding") or {}
    base = str(config.get("base_url") or DEFAULT_BASE)
    replacements = {
        "LLM_PROVIDER": str(llm.get("provider") or "ollama"),
        "LLM_BASE_URL": base,
        "LLM_MODEL": str(llm.get("model") or "qwen2.5:7b"),
        "LLM_TEMPERATURE": str(llm.get("temperature") if llm.get("temperature") is not None else "0.1"),
        "EMBEDDING_PROVIDER": str(emb.get("provider") or "ollama"),
        "EMBEDDING_MODEL": str(emb.get("model") or "nomic-embed-text"),
        "EMBEDDING_BASE_URL": base,
    }

    lines = path.read_text(encoding="utf-8").splitlines()
    found: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in replacements:
            new_lines.append(f"{key}={replacements[key]}")
            found.add(key)
        else:
            new_lines.append(line)
    for key, value in replacements.items():
        if key not in found:
            new_lines.append(f"{key}={value}")
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f".env szinkronizálva a models.json alapján ({path.name}).")


def refresh_path() -> None:
    """Frissíti az aktuális folyamat PATH-ját Windows User/Machine változókból."""
    if os.name != "nt":
        return
    try:
        import winreg

        paths: list[str] = []
        for hive, subkey in (
            (winreg.HKEY_CURRENT_USER, r"Environment"),
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        ):
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    value, _ = winreg.QueryValueEx(key, "Path")
                    paths.extend(value.split(";"))
            except OSError:
                continue
        current = os.environ.get("PATH", "").split(";")
        merged = []
        seen = set()
        for item in paths + current:
            cleaned = item.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                merged.append(cleaned)
        os.environ["PATH"] = ";".join(merged)
    except Exception:
        pass


def start_ollama(ollama_bin: str | None = None) -> None:
    binary = ollama_bin or which_ollama()
    if not binary:
        raise RuntimeError("Az ollama parancs nem található a telepítés után.")
    if api_ready():
        print("Ollama API már fut.")
        return
    print("Ollama szolgáltatás indítása...")
    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
        kwargs["creationflags"] = creationflags
        app = Path(binary).with_name("ollama app.exe")
        if app.is_file():
            subprocess.Popen([str(app)], **kwargs)
        else:
            subprocess.Popen([binary, "serve"], **kwargs)
    else:
        kwargs["start_new_session"] = True
        systemctl = shutil.which("systemctl")
        if systemctl:
            subprocess.run(
                [systemctl, "start", "ollama"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        if not api_ready():
            subprocess.Popen([binary, "serve"], **kwargs)


def wait_for_api(base_url: str = DEFAULT_BASE, seconds: int = 90) -> bool:
    print(f"Ollama API várása ({base_url})...")
    deadline = time.time() + seconds
    while time.time() < deadline:
        if api_ready(base_url):
            print("Ollama API elérhető.")
            return True
        time.sleep(1.5)
    return False


def _download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "LocalAIChatbotInstaller/1.0"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        chunk_size = 1024 * 256
        last_pct = -1
        with destination.open("wb") as handle:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = int(downloaded * 100 / total)
                    if pct != last_pct and pct % 5 == 0:
                        mb = downloaded / (1024 * 1024)
                        total_mb = total / (1024 * 1024)
                        print(f"  Letöltés: {pct}% ({mb:.1f}/{total_mb:.1f} MB)", flush=True)
                        last_pct = pct
    if destination.stat().st_size < 1_000_000:
        raise RuntimeError(
            f"A letöltött installer gyanúsan kicsi ({destination.stat().st_size} bájt). "
            f"Ellenőrizd a hálózatot, majd nyisd meg: {url}"
        )


def _winget_install_ollama(winget: str) -> bool:
    print("Ollama telepítése winget-tel (--source winget)...")
    result = subprocess.run(
        [
            winget,
            "install",
            "-e",
            "--id",
            "Ollama.Ollama",
            "--source",
            "winget",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--disable-interactivity",
        ],
        check=False,
    )
    ok_codes = {0, -1978335189, -1978334962}
    if result.returncode in ok_codes:
        refresh_path()
        time.sleep(2)
        if which_ollama():
            print("Winget telepítés sikeres.")
            return True
        print("Winget lefutott, de az ollama.exe még nem található. Fallback következik...")
        return False
    print(f"A winget telepítés nem sikerült (kód: {result.returncode}).")
    return False


def install_windows() -> None:
    winget = shutil.which("winget")
    if winget and _winget_install_ollama(winget):
        return

    print("OllamaSetup.exe letöltése az ollama.com-ról...")
    install_dir = ROOT / "storage" / "models"
    install_dir.mkdir(parents=True, exist_ok=True)
    installer = install_dir / "OllamaSetup.exe"
    _download_file(WINDOWS_SETUP_URL, installer)
    print("Ollama telepítő futtatása (megjelenhet telepítő ablak)...")
    completed = subprocess.run([str(installer), "/VERYSILENT", "/NORESTART"], check=False)
    if completed.returncode != 0 or not which_ollama():
        refresh_path()
        if not which_ollama():
            completed = subprocess.run([str(installer), "/SILENT", "/NORESTART"], check=False)
    if completed.returncode != 0 and not which_ollama():
        print("Silent telepítés nem sikerült, GUI telepítő indítása...")
        completed = subprocess.run([str(installer)], check=False)
    refresh_path()
    time.sleep(3)
    if not which_ollama():
        print("Várakozás a telepítés befejezésére...")
        deadline = time.time() + 180
        while time.time() < deadline and not which_ollama():
            refresh_path()
            time.sleep(2)
    if not which_ollama():
        raise RuntimeError(
            "Az OllamaSetup.exe lefutott, de az ollama.exe nem található. "
            "Telepítsd kézzel: https://ollama.com/download majd futtasd újra az install.bat-ot."
        )


def install_linux() -> None:
    print("Ollama telepítése a hivatalos install.sh scripttel...")
    curl = shutil.which("curl")
    if not curl:
        raise RuntimeError("A curl parancs szükséges az Ollama Linux telepítéséhez.")
    script = urllib.request.urlopen(LINUX_INSTALL_URL, timeout=60).read()
    proc = subprocess.run(
        ["sh", "-s", "--"],
        input=script,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Az Ollama Linux telepítő hibával lépett ki (kód: {proc.returncode}).")


def ensure_ollama(
    base_url: str = DEFAULT_BASE,
    skip_install: bool = False,
    *,
    models_json: Path | None = None,
    skip_models: bool = False,
    sync_env: bool = True,
) -> int:
    config = load_models_config(models_json)
    base_url = str(config.get("base_url") or base_url or DEFAULT_BASE)

    refresh_path()
    existing = which_ollama()
    runtime_ok = False

    if existing and api_ready(base_url):
        print(f"Ollama már telepítve és fut: {existing}")
        runtime_ok = True
    elif existing and not api_ready(base_url):
        print(f"Ollama megtalálva ({existing}), de az API nem fut.")
        start_ollama(existing)
        runtime_ok = wait_for_api(base_url)
        if not runtime_ok:
            print("FIGYELEM: Az Ollama API nem indult el automatikusan.")
    elif skip_install:
        print("Ollama nincs telepítve, és a telepítés ki van kapcsolva (--skip-install).")
    else:
        print("Ollama nincs telepítve. Telepítés indul...")
        if os.name == "nt":
            install_windows()
        elif sys.platform.startswith("linux"):
            install_linux()
        else:
            raise RuntimeError(
                f"Nem támogatott platform automatikus Ollama telepítéshez: {sys.platform}. "
                "Telepítsd kézzel: https://ollama.com/download"
            )

        refresh_path()
        binary = which_ollama()
        if not binary:
            print(
                "Az Ollama települt, de a parancs még nem látszik ebben a sessionben. "
                "Próbáld újraindítani a terminált, vagy indítsd kézzel az Ollama alkalmazást."
            )
            start_ollama(None)
        else:
            print(f"Ollama telepítve: {binary}")
            start_ollama(binary)

        runtime_ok = wait_for_api(base_url, seconds=120)
        if not runtime_ok:
            print(
                "FIGYELEM: Az Ollama telepítése megtörtént, de az API még nem elérhető. "
                "Indítsd el az Ollama alkalmazást, majd futtasd újra: scripts/check_llm.py"
            )

    if sync_env:
        try:
            sync_env_from_models(config)
        except Exception as exc:
            print(f"FIGYELEM: .env szinkronizálás sikertelen: {exc}")

    if not runtime_ok:
        return 1

    print("=== Modellek a models.json alapján ===")
    for name in model_names_to_pull(config):
        print(f"  - {name}")
    return ensure_models(config, skip_pull=skip_models)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ollama telepítése, indítása és modellek letöltése (models.json)"
    )
    parser.add_argument("--base-url", default=None, help="Felülírja a models.json base_url értékét")
    parser.add_argument(
        "--models-json",
        default=str(DEFAULT_MODELS_JSON),
        help="Modellkonfig JSON útvonala (default: ./models.json)",
    )
    parser.add_argument("--skip-install", action="store_true", help="Csak indítás / ellenőrzés")
    parser.add_argument("--skip-models", action="store_true", help="Ne töltse le a modelleket")
    parser.add_argument("--no-sync-env", action="store_true", help="Ne írja át a .env fájlt")
    args = parser.parse_args()
    try:
        config = load_models_config(Path(args.models_json))
        base = args.base_url or str(config.get("base_url") or DEFAULT_BASE)
        return ensure_ollama(
            base_url=base,
            skip_install=args.skip_install,
            models_json=Path(args.models_json),
            skip_models=args.skip_models,
            sync_env=not args.no_sync_env,
        )
    except urllib.error.URLError as exc:
        print(f"Hálózati hiba az Ollama telepítésekor: {exc}")
        return 1
    except Exception as exc:
        print(f"Ollama telepítési hiba: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
