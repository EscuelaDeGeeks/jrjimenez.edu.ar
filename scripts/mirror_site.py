#!/usr/bin/env python3
"""Mirror juanramonjimenez-pulgarin.com as a static site with local assets."""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

BASE_URL = "https://juanramonjimenez-pulgarin.com/"
DOMAIN = "juanramonjimenez-pulgarin.com"
ROOT = Path(__file__).resolve().parent.parent
SITEMAP = f"{BASE_URL}wp-sitemap.xml"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

ASSET_EXTENSIONS = {
    ".css", ".js", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".ico", ".mp4", ".webm", ".pdf",
}
SKIP_PATH_PREFIXES = ("/wp-admin/", "/wp-login", "/xmlrpc.php")
SKIP_EXTENSIONS = {".php"}


def curl_download(url: str, dest: Path, retries: int = 4) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries):
        result = subprocess.run(
            [
                "curl", "-fsSL", "--retry", "3", "--retry-delay", "1",
                "-A", "StaticMirror/1.0", "-o", str(dest), url,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
            return True
        time.sleep(0.5 * (attempt + 1))
    return False


def curl_body(url: str, retries: int = 4) -> bytes | None:
    for attempt in range(retries):
        result = subprocess.run(
            [
                "curl", "-fsSL", "--retry", "3", "--retry-delay", "1",
                "-A", "StaticMirror/1.0", url,
            ],
            capture_output=True,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        time.sleep(0.5 * (attempt + 1))
    return None


def sanitize_path(url: str) -> Path:
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
    return Path(rel)


def is_same_site(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", ""):
        return False
    if parsed.netloc and parsed.netloc != DOMAIN:
        return False
    path = parsed.path or "/"
    for prefix in SKIP_PATH_PREFIXES:
        if path.startswith(prefix):
            return False
    if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
        return False
    return True


def is_page_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path.startswith("/wp-content/") or path.startswith("/wp-includes/"):
        return False
    if path.startswith("/wp-json"):
        return False
    ext = Path(path).suffix.lower()
    if ext in ASSET_EXTENSIONS:
        return False
    if ext in SKIP_EXTENSIONS:
        return False
    return True


def is_asset_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path or "/"
    ext = Path(path).suffix.lower()
    if ext in ASSET_EXTENSIONS:
        return True
    if path.startswith("/wp-content/") or path.startswith("/wp-includes/"):
        return True
    return False


def normalize_url(url: str, base: str = BASE_URL) -> str:
    joined = urljoin(base, url)
    parsed = urlparse(joined)
    clean = parsed._replace(fragment="")
    return urlunparse(clean)


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        for key in ("href", "src", "data-src", "data-lazy-src", "poster"):
            val = attr_map.get(key)
            if val:
                self.links.add(val)
        srcset = attr_map.get("srcset")
        if srcset:
            for part in srcset.split(","):
                piece = part.strip().split(" ", 1)[0]
                if piece:
                    self.links.add(piece)


def extract_urls_from_css(css: str, base_url: str) -> set[str]:
    urls: set[str] = set()
    for match in re.finditer(r"url\((['\"]?)([^)'\"]+)\1\)", css, re.I):
        urls.add(normalize_url(match.group(2).strip(), base_url))
    for match in re.finditer(r"@import\s+(['\"])([^'\"]+)\1", css, re.I):
        urls.add(normalize_url(match.group(2).strip(), base_url))
    return urls


def fetch_sitemap_urls() -> list[str]:
    body = curl_body(SITEMAP)
    if not body:
        raise RuntimeError("Failed to fetch sitemap index")
    root = ET.fromstring(body)
    urls: list[str] = []
    for sitemap in root.findall("sm:sitemap/sm:loc", NS):
        sub_body = curl_body(sitemap.text.strip())
        if not sub_body:
            continue
        sub_root = ET.fromstring(sub_body)
        for loc in sub_root.findall("sm:url/sm:loc", NS):
            urls.append(loc.text.strip())
    return urls


def rewrite_html(content: str, page_url: str, url_to_local: dict[str, str]) -> str:
    def repl_attr(match: re.Match[str]) -> str:
        quote = match.group(1)
        raw = match.group(2)
        if raw.startswith(("data:", "mailto:", "tel:", "javascript:", "#")):
            return match.group(0)
        abs_url = normalize_url(raw, page_url)
        if abs_url in url_to_local:
            return f"{match.group(0).split('=')[0]}={quote}{url_to_local[abs_url]}{quote}"
        return match.group(0)

    content = re.sub(
        r"""(?:href|src|data-src|data-lazy-src|poster)\s*=\s*(['"])([^'"]+)\1""",
        repl_attr,
        content,
        flags=re.I,
    )

    def repl_css_url(match: re.Match[str]) -> str:
        raw = match.group(2).strip()
        if raw.startswith("data:"):
            return match.group(0)
        abs_url = normalize_url(raw, page_url)
        if abs_url in url_to_local:
            return f"url({match.group(1)}{url_to_local[abs_url]}{match.group(1)})"
        return match.group(0)

    content = re.sub(
        r"url\((['\"]?)([^)'\"]+)\1\)",
        repl_css_url,
        content,
        flags=re.I,
    )
    return content


def main() -> int:
    print("Fetching sitemap URLs...")
    seed_pages = fetch_sitemap_urls()
    print(f"  {len(seed_pages)} URLs from sitemap")

    pages_todo: list[str] = []
    seen_pages: set[str] = set()
    for u in seed_pages + [BASE_URL]:
        nu = normalize_url(u)
        if is_same_site(nu) and is_page_url(nu) and nu not in seen_pages:
            seen_pages.add(nu)
            pages_todo.append(nu)

    assets_todo: set[str] = set()
    downloaded: dict[str, Path] = {}
    url_to_local: dict[str, str] = {}

    def local_key(url: str) -> str:
        rel = sanitize_path(url)
        return rel.as_posix()

    def download_resource(url: str) -> Path | None:
        if url in downloaded:
            return downloaded[url]
        dest = ROOT / sanitize_path(url)
        if dest.exists() and dest.stat().st_size > 0:
            downloaded[url] = dest
            url_to_local[url] = dest.relative_to(ROOT).as_posix()
            return dest
        print(f"  GET {url}")
        if not curl_download(url, dest):
            print(f"  FAIL {url}", file=sys.stderr)
            return None
        downloaded[url] = dest
        url_to_local[url] = dest.relative_to(ROOT).as_posix()
        return dest

    idx = 0
    while idx < len(pages_todo):
        page_url = pages_todo[idx]
        idx += 1
        print(f"[page {idx}/{len(pages_todo)}] {page_url}")
        body = curl_body(page_url)
        if not body:
            print(f"  skip (no body): {page_url}", file=sys.stderr)
            continue

        html = body.decode("utf-8", errors="replace")
        parser = LinkExtractor()
        parser.feed(html)

        for raw in list(parser.links):
            abs_url = normalize_url(raw, page_url)
            if not is_same_site(abs_url):
                continue
            if is_page_url(abs_url) and abs_url not in seen_pages:
                seen_pages.add(abs_url)
                pages_todo.append(abs_url)
            elif is_asset_url(abs_url):
                assets_todo.add(abs_url)

        dest = ROOT / sanitize_path(page_url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        downloaded[page_url] = dest
        url_to_local[page_url] = dest.relative_to(ROOT).as_posix()

    print(f"\nDownloading {len(assets_todo)} assets...")
    pending = list(assets_todo)
    css_queue: list[tuple[str, str]] = []

    for i, asset_url in enumerate(pending, 1):
        print(f"[asset {i}/{len(pending)}] {asset_url}")
        dest = download_resource(asset_url)
        if not dest:
            continue
        if dest.suffix.lower() == ".css" or "@ver=" in dest.name:
            try:
                css_text = dest.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for ref in extract_urls_from_css(css_text, asset_url):
                if not is_same_site(ref):
                    continue
                if is_asset_url(ref) and ref not in assets_todo and ref not in downloaded:
                    pending.append(ref)
                    assets_todo.add(ref)
                    print(f"  + css ref {ref}")

    print("\nRewriting links in HTML and CSS...")
    for url, path in list(downloaded.items()):
        if path.suffix.lower() not in {".html", ".css"} and not path.name.endswith(".css"):
            if "css" not in path.name:
                continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        base_page = url if url.endswith((".html", "/")) or is_page_url(url) else BASE_URL
        rewritten = rewrite_html(text, base_page, url_to_local)
        if rewritten != text:
            path.write_text(rewritten, encoding="utf-8")

    # Pretty URLs: copy section folders if only index.html exists
    for page_url in seen_pages:
        parsed = urlparse(page_url)
        if not parsed.path.endswith("/"):
            continue
        src = ROOT / sanitize_path(page_url)
        if src.name == "index.html" and src.exists():
            folder_index = src
            alt = ROOT / (parsed.path.strip("/") + ".html")
            if not alt.exists():
                alt.write_bytes(folder_index.read_bytes())

    print(f"\nDone. Pages: {len(seen_pages)}, files: {len(downloaded)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())