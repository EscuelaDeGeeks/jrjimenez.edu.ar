"""Use root-absolute paths for wp-content and wp-includes assets on GitHub Pages."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "scripts", "agent-tools", "terminals", "mcps"}

# href/src/url() values that should be site-root absolute
PREFIXES = ("wp-content/", "wp-includes/", "../wp-content/", "../wp-includes/")
ATTR = re.compile(
    r"""(?P<attr>href|src|data-src|data-lazy-src|poster)\s*=\s*(['"])(?P<val>(?:\.\./)?(?:wp-content|wp-includes)/[^'"]+)\2""",
    re.I,
)
CSS_URL = re.compile(
    r"""url\((['"]?)((?:\.\./)?(?:wp-content|wp-includes)/[^)'"]+)\1\)""",
    re.I,
)
JSON_ESC = re.compile(
    r"""(?P<q>['"])((?:\\?\./)?(?:wp-content|wp-includes)\\?/[^'"]+)(?P=q)""",
)


def to_root(val: str) -> str:
    while val.startswith("../"):
        val = val[3:]
    if val.startswith("/"):
        return val
    return "/" + val


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text

    def attr_repl(m: re.Match[str]) -> str:
        val = to_root(m.group("val"))
        return f"{m.group('attr')}={m.group(2)}{val}{m.group(2)}"

    text = ATTR.sub(attr_repl, text)

    def css_repl(m: re.Match[str]) -> str:
        q = m.group(1) or ""
        val = to_root(m.group(2))
        return f"url({q}{val}{q})"

    text = CSS_URL.sub(css_repl, text)

    # JSON-escaped paths in inline scripts (elementor config)
    def esc_repl(m: re.Match[str]) -> str:
        raw = m.group(2)
        if raw.startswith("\\/"):
            val = "/" + raw.replace("\\/", "/").lstrip("/")
            esc = val.replace("/", "\\/")
            return f'"{esc}"'
        return m.group(0)

    text = JSON_ESC.sub(esc_repl, text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    n = 0
    for ext in ("*.html", "*.css"):
        for path in ROOT.rglob(ext):
            if SKIP.intersection(path.parts):
                continue
            if patch(path):
                n += 1
    print(f"root-absolute paths in {n} files")


if __name__ == "__main__":
    main()