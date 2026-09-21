"""Futó backend és worker folyamatok leállítása."""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PID_FILE = ROOT / "storage" / "runtime.pids"


def main() -> int:
    if not PID_FILE.exists():
        print("Nincs futó példány (runtime.pids hiányzik).")
        return 0
    pids = [int(item) for item in PID_FILE.read_text(encoding="utf-8").split() if item.strip().isdigit()]
    for pid in pids:
        try:
            if os.name == "nt":
                os.kill(pid, signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGTERM)
            print(f"Leállítva: PID {pid}")
        except OSError:
            print(f"Már nem fut: PID {pid}")
    time.sleep(1)
    if os.name == "nt":
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    if PID_FILE.exists():
        PID_FILE.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
