"""Replace JSON-escaped and HTML-encoded remote asset URLs."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

DOMAIN = "juanramonjimenez-pulgarin.com"
BASE = f"https://{DOMAIN}/"
ROOT = Path(__file__).resolve().parent.parent
SKIP_PARTS = {".git", "scripts", "agent-tools", "terminals", "mcps"}

# Any juanramonjimenez URL with optional backslash-escaped slashes
REMOTE = re.compile(
    rf"https?:\\?/\\?/{re.escape(DOMAIN)}((?:\\?/[^\"'&\s<>]+)+)",
    re.I,
)


def normalize_path(raw: str) -> str:
    path = raw.replace("\\/", "/").replace("\\", "")
    if not path.startswith("/"):
        path = "/" + path
    return path


def resolve(path: str) -> str | None:
    rel = path.lstrip("/")
    for cand in (ROOT / rel,):
        if cand.exists() and cand.stat().st_size > 0:
            return cand.relative_to(ROOT).as_posix()
    dest = ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = BASE + rel
    r = subprocess.run(["curl", "-fsSL", "-o", str(dest), url], capture_output=True)
    if r.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
        return rel
    return None


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text

    for m in sorted(set(REMOTE.findall(text)), key=len, reverse=True):
        norm = normalize_path(m)
        if "wp-json" in norm or "admin-ajax" in norm or "xmlrpc" in norm:
            continue
        local = resolve(norm)
        if not local:
            continue
        rel = os.path.relpath(ROOT / local, path.parent).replace("\\", "/")
        # Replace both escaped and unescaped forms
        for old in (
            f"https://{DOMAIN}{norm}",
            f"https:\\/\\/{DOMAIN}{m}",
            f"https://{DOMAIN}{m.replace(chr(92)+'/', '/')}",
        ):
            text = text.replace(old, rel)
        esc_rel = rel.replace("/", "\\/")
        text = text.replace(f"https:\\/\\/{DOMAIN}{m}", esc_rel)

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    n = sum(
        1
        for p in ROOT.rglob("*.html")
        if not SKIP_PARTS.intersection(p.parts) and patch(p)
    )
    print(f"fixed escaped URLs in {n} files")


if __name__ == "__main__":
    main()