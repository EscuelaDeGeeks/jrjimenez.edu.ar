#!/usr/bin/env python3
"""Repair local paths and fetch remaining same-origin assets."""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

DOMAIN = "juanramonjimenez-pulgarin.com"
BASE = f"https://{DOMAIN}/"
ROOT = Path(__file__).resolve().parent.parent
SKIP_URL_SUBSTR = ("window.location", "${", "t.params", "Ji(e", "admin-ajax", "xmlrpc.php", "/wp-json/")

REMOTE_RE = re.compile(
    rf"https?://{re.escape(DOMAIN)}(/[^\"'\\s<>)]+)",
    re.I,
)
BROKEN_RE = re.compile(r"""wp-content_[a-z0-9_.@-]+""", re.I)


def url_to_local_path(url: str) -> Path:
    parsed = urlparse(url)
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
    return ROOT / rel


def local_candidates(url: str) -> list[Path]:
    base = url_to_local_path(url)
    out = [base]
    if ".css" in base.name:
        out.append(base.with_name(base.name + ".css"))
    return out


def curl_download(url: str, dest: Path) -> bool:
    if any(s in url for s in SKIP_URL_SUBSTR):
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["curl", "-fsSL", "--retry", "2", "--max-time", "30", "-o", str(dest), url],
        capture_output=True,
    )
    return r.returncode == 0 and dest.exists() and dest.stat().st_size > 0


def broken_to_url(token: str) -> str | None:
    if not token.startswith("wp-content_"):
        return None
    rest = token[len("wp-content_") :]
    if "@" in rest:
        path_part, query = rest.split("@", 1)
        query = "?" + query
    else:
        path_part, query = rest, ""
    path = "wp-content/" + path_part.replace("_", "/")
    return urljoin(BASE, path + query)


def collect_target_files() -> list[Path]:
    return [
        p
        for p in ROOT.rglob("*")
        if p.is_file()
        and p.suffix.lower() in {".html", ".css"}
        and "scripts" not in p.parts
        and ".git" not in p.parts
        and "agent-tools" not in p.parts
    ]


def collect_urls(files: list[Path]) -> set[str]:
    urls: set[str] = set()
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in REMOTE_RE.finditer(text):
            urls.add(f"https://{DOMAIN}{m.group(1)}")
        for token in BROKEN_RE.findall(text):
            u = broken_to_url(token)
            if u:
                urls.add(u)
        for m in re.finditer(rf"https?:\\/\\/{re.escape(DOMAIN)}([^\"'\\s]+)", text):
            urls.add(m.group(0).replace("\\/", "/"))
    return {u for u in urls if not any(s in u for s in SKIP_URL_SUBSTR)}


def build_cache() -> dict[str, str]:
    cache: dict[str, str] = {}
    for f in ROOT.rglob("*"):
        if not f.is_file() or ".git" in f.parts or f.parts[0] == "scripts":
            continue
        rel = f.relative_to(ROOT).as_posix()
        name = f.name
        if "@" in name:
            base, q = name.split("@", 1)
            q = q.removesuffix(".css")
            path = (f.parent / base).as_posix()
            cache[f"{BASE}{path}?{q}"] = rel
        cache[f"{BASE}{rel}"] = rel
    return cache


def resolve(url: str, cache: dict[str, str]) -> str | None:
    if url in cache:
        return cache[url]
    for cand in local_candidates(url):
        if cand.exists() and cand.stat().st_size > 0:
            rel = cand.relative_to(ROOT).as_posix()
            cache[url] = rel
            return rel
    dest = url_to_local_path(url)
    print(f"fetch {url}")
    if curl_download(url, dest):
        rel = dest.relative_to(ROOT).as_posix()
        cache[url] = rel
        return rel
    for cand in local_candidates(url):
        if cand.exists():
            rel = cand.relative_to(ROOT).as_posix()
            cache[url] = rel
            return rel
    return None


def to_relative(local_posix: str, from_file: Path) -> str:
    return os.path.relpath(ROOT / local_posix, from_file.parent).replace("\\", "/")


def patch(path: Path, cache: dict[str, str]) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text

    for token in set(BROKEN_RE.findall(text)):
        url = broken_to_url(token)
        if not url:
            continue
        local = cache.get(url) or resolve(url, cache)
        if local:
            text = text.replace(token, to_relative(local, path))

    for m in list(REMOTE_RE.finditer(text)):
        url = f"https://{DOMAIN}{m.group(1)}"
        local = cache.get(url) or resolve(url, cache)
        if local:
            text = text.replace(m.group(0), to_relative(local, path))

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    print("fix_static_links: start", flush=True)
    files = collect_target_files()
    print(f"Scanning {len(files)} files...", flush=True)
    urls = collect_urls(files)
    print(f"Found {len(urls)} unique same-origin URLs")
    cache = build_cache()
    for i, url in enumerate(sorted(urls), 1):
        if url in cache:
            continue
        found = False
        for cand in local_candidates(url):
            if cand.exists() and cand.stat().st_size > 0:
                cache[url] = cand.relative_to(ROOT).as_posix()
                found = True
                break
        if not found:
            resolve(url, cache)
        if i % 25 == 0:
            print(f"  resolved {i}/{len(urls)}")
    changed = sum(patch(f, cache) for f in files)
    print(f"Patched {changed} files; cache size {len(cache)}")


if __name__ == "__main__":
    main()