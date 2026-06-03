"""Copy @ver-suffixed asset files to plain names for static hosting."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "scripts", "agent-tools", "terminals", "mcps"}


def main() -> None:
    created = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or SKIP.intersection(path.parts):
            continue
        if "@" not in path.name:
            continue
        base_name = path.name.split("@", 1)[0]
        if not base_name.endswith((".css", ".js", ".woff", ".woff2", ".ttf", ".svg")):
            continue
        dest = path.parent / base_name
        if dest.exists() and dest.stat().st_size > 0:
            continue
        if path.stat().st_size == 0:
            continue
        shutil.copy2(path, dest)
        created += 1
    print(f"materialized {created} plain asset files")


if __name__ == "__main__":
    main()