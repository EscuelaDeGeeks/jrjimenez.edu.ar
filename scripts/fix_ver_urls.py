"""Strip @ver= query suffixes from asset URLs for correct GitHub Pages MIME types."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_PARTS = {".git", "scripts", "agent-tools", "terminals", "mcps"}

# WordPress mirror stores ?ver= as @ver= in filenames; browsers need .css/.js paths.
VER_SUFFIX = re.compile(
    r"(@ver=[0-9a-zA-Z._-]+|@bhinol)",
    re.I,
)


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text
    text = VER_SUFFIX.sub("", text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    for ext in ("*.html", "*.css", "*.js"):
        for path in ROOT.rglob(ext):
            if SKIP_PARTS.intersection(path.parts):
                continue
            if patch_file(path):
                changed += 1
    print(f"stripped @ver from {changed} files")


if __name__ == "__main__":
    main()