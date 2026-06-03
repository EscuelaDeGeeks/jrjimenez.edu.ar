"""Replace all localizable juanramonjimenez-pulgarin.com URLs with relative paths."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

DOMAIN = "juanramonjimenez-pulgarin.com"
BASE = f"https://{DOMAIN}"
ROOT = Path(__file__).resolve().parent.parent
SKIP_PARTS = {".git", "scripts", "agent-tools", "terminals", "mcps"}

SKIP_URL = ("/wp-json/", "admin-ajax", "xmlrpc.php", "oembed/1.0")

# Match absolute and JSON-escaped URLs
URL_PATTERNS = [
    re.compile(rf"https?://{re.escape(DOMAIN)}(/[a-zA-Z0-9_./%-]+(?:\?[a-zA-Z0-9_=&%.-]+)?)", re.I),
    re.compile(rf"https?:\\/\\/{re.escape(DOMAIN)}(\\/[a-zA-Z0-9_./%-]+)", re.I),
]
HOME_URL = re.compile(rf"https?://{re.escape(DOMAIN)}/?(?=[\"'\\s<>]|$)", re.I)
HOME_ESC = re.compile(rf"https?:\\/\\/{re.escape(DOMAIN)}\\/?(?=[\"'\\s]|$)", re.I)


def url_to_local(url: str) -> str | None:
    url = url.replace("\\/", "/")
    parsed = urlparse(url)
    if any(s in (parsed.path + (parsed.query or "")) for s in SKIP_URL):
        return None
    path = parsed.path or "/"
    if path == "/":
        return "index.html"
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


def download(url: str) -> str | None:
    parsed = urlparse(url.replace("\\/", "/"))
    if any(s in (parsed.path + (parsed.query or "")) for s in SKIP_URL):
        return None
    path = parsed.path or "/"
    if path.endswith("/"):
        return None
    rel = path.lstrip("/")
    if parsed.query:
        p = Path(rel)
        stem = f"{p.name}@{parsed.query.replace('/', '_')}"
        rel = str(p.parent / stem) if str(p.parent) not in (".", "") else stem
    dest = ROOT / rel
    if dest.exists() and dest.stat().st_size > 0:
        return rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["curl", "-fsSL", "--retry", "2", "--max-time", "45", "-o", str(dest), url.replace("\\/", "/")],
        capture_output=True,
    )
    if r.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
        return rel
    return None


def collect_urls(text: str) -> set[str]:
    urls: set[str] = set()
    for pat in URL_PATTERNS:
        for m in pat.finditer(text):
            if pat.pattern.find("\\/") >= 0:
                urls.add(f"{BASE}{m.group(1).replace(chr(92)+'/', '/')}")
            else:
                urls.add(f"{BASE}{m.group(1)}")
    return urls


def patch_file(path: Path, cache: dict[str, str]) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text

    for url in sorted(collect_urls(text), key=len, reverse=True):
        if url in cache:
            local = cache[url]
        else:
            local = url_to_local(url) or download(url)
            if local:
                cache[url] = local
            else:
                continue
        rel = os.path.relpath(ROOT / local, path.parent).replace("\\", "/")
        text = text.replace(url, rel)
        esc = url.replace("/", "\\/")
        if esc != url:
            text = text.replace(esc, rel.replace("/", "\\/"))

    depth = len(path.parent.relative_to(ROOT).parts) if path.parent != ROOT else 0
    home = "index.html" if depth == 0 else "../" * depth + "index.html"
    text = HOME_URL.sub(home, text)
    text = HOME_ESC.sub(home.replace("/", "\\/"), text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    cache: dict[str, str] = {f"{BASE}/": "index.html", BASE: "index.html"}
    changed = 0
    for p in sorted(ROOT.rglob("*.html")):
        if SKIP_PARTS.intersection(p.parts):
            continue
        if patch_file(p, cache):
            changed += 1
    print(f"localized {changed} files; {len(cache)} cached paths")


if __name__ == "__main__":
    main()