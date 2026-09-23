"""Hiányzó .env kulcsok pótlása az .env.example alapján."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_env_entries(text: str) -> list[tuple[str, str]]:
    """KEY=value párok az első előfordulás sorrendjében (kommentek kihagyva)."""
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        entries.append((key, value))
    return entries


def parse_env_keys(text: str) -> set[str]:
    return {key for key, _ in parse_env_entries(text)}


def merge_env_from_example(
    env_path: Path | None = None,
    example_path: Path | None = None,
) -> list[str]:
    """
    Az .env.example kulcsait, amelyek hiányoznak a .env-ből, hozzáfűzi
    az example-beli értékkel. Ha nincs .env, az egészet átmásolja.

    Visszaadja a hozzáadott kulcsok listáját.
    """
    env_path = env_path or (ROOT / ".env")
    example_path = example_path or (ROOT / ".env.example")

    if not example_path.is_file():
        return []

    example_text = example_path.read_text(encoding="utf-8")
    example_entries = parse_env_entries(example_text)

    if not env_path.is_file():
        env_path.write_text(example_text, encoding="utf-8")
        return [key for key, _ in example_entries]

    existing = parse_env_keys(env_path.read_text(encoding="utf-8"))
    missing = [(key, value) for key, value in example_entries if key not in existing]
    if not missing:
        return []

    env_text = env_path.read_text(encoding="utf-8")
    if env_text and not env_text.endswith("\n"):
        env_text += "\n"
    if env_text and not env_text.endswith("\n\n"):
        env_text += "\n"
    block = "\n".join(f"{key}={value}" for key, value in missing) + "\n"
    env_path.write_text(env_text + block, encoding="utf-8")
    return [key for key, _ in missing]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Hiányzó .env kulcsok pótlása az .env.example-ből",
    )
    parser.add_argument("--env", type=Path, default=None, help=".env útvonal")
    parser.add_argument("--example", type=Path, default=None, help=".env.example útvonal")
    args = parser.parse_args(argv)

    example = args.example or (ROOT / ".env.example")
    env_file = args.env or (ROOT / ".env")

    if not example.is_file():
        print(f"FIGYELEM: nincs .env.example ({example})", file=sys.stderr)
        return 1

    created = not env_file.is_file()
    added = merge_env_from_example(env_path=env_file, example_path=example)
    if created:
        print(f".env létrehozva az .env.example alapján ({env_file.name}).")
    elif added:
        print(f".env kiegészítve {len(added)} hiányzó kulccsal: {', '.join(added)}")
    else:
        print(".env naprakész (minden .env.example kulcs megvan).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
