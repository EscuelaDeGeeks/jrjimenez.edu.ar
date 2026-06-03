"""Fix .css=3.4.4 artifacts left when @ver was stripped incompletely."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "scripts", "agent-tools", "terminals", "mcps"}

BROKEN = re.compile(r"\.(css|js|woff2?)=[0-9a-zA-Z._-]+")
REL_WP = re.compile(r"(?:\.\./)+(?=(?:wp-content|wp-includes)/)")


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text
    text = BROKEN.sub(r".\1", text)
    text = REL_WP.sub("/", text)
    # Ensure wp-content/wp-includes in attributes use root absolute
    text = re.sub(
        r"""(?P<a>href|src|content|srcset)\s*=\s*(['"])(?:\.\./)*(?P<p>(?:wp-content|wp-includes)/[^'"]+)""",
        lambda m: f"{m.group('a')}={m.group(2)}/{m.group('p')}",
        text,
        flags=re.I,
    )
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    n = sum(1 for p in ROOT.rglob("*.html") if not SKIP.intersection(p.parts) and patch(p))
    print(f"fixed ver suffix / relative paths in {n} files")


if __name__ == "__main__":
    main()