"""Replace remaining absolute site URLs when a local file already exists."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

DOMAIN = "juanramonjimenez-pulgarin.com"
BASE = f"https://{DOMAIN}"
ROOT = Path(__file__).resolve().parent.parent

REMOTE = re.compile(
    rf"https?://{re.escape(DOMAIN)}(/[a-zA-Z0-9_./%-]+(?:\?[a-zA-Z0-9_=&%.-]+)?)",
    re.I,
)
ESCAPED = re.compile(
    rf"https?:\\/\\/{re.escape(DOMAIN)}(\\/wp-content\\/[^\"'\\s]+)",
    re.I,
)
SKIP = ("/wp-json/", "admin-ajax", "xmlrpc.php", "oembed")


def url_to_local(url: str) -> str | None:
    parsed = urlparse(url.replace("\\/", "/"))
    if any(s in (parsed.path + (parsed.query or "")) for s in SKIP):
        return None
    path = parsed.path or "/"
    if path.endswith("/"):
        path += "index.html"
    elif not Path(path).suffix:
        path += ".html"
    rel = path.lstrip("/")
    if parsed.query:
        p = Path(rel)
        stem = f"{p.name}@{parsed.query.replace('/', '_')}"
        rel = str(p.parent / stem) if str(p.parent) not in (".", "") else stem
    for cand in (ROOT / rel, ROOT / f"{rel}.css"):
        if cand.exists() and cand.stat().st_size > 0:
            return cand.relative_to(ROOT).as_posix()
    return None


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text
    for m in sorted(set(REMOTE.findall(text)), key=len, reverse=True):
        url = f"{BASE}{m}"
        local = url_to_local(url)
        if local:
            rel = os.path.relpath(ROOT / local, path.parent).replace("\\", "/")
            text = text.replace(url, rel)
    for m in ESCAPED.findall(text):
        url = f"{BASE}{m.replace(chr(92)+'/', '/')}"
        local = url_to_local(url)
        if local:
            rel = os.path.relpath(ROOT / local, path.parent).replace("\\", "/")
            text = text.replace(f"https:\\/\\/{DOMAIN}{m}", rel.replace("/", "\\/"))
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    n = 0
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".html", ".css"}:
            continue
        if any(x in p.parts for x in (".git", "scripts", "agent-tools")):
            continue
        if patch(p):
            n += 1
    print(f"localized {n} files (existing assets only)")


if __name__ == "__main__":
    main()