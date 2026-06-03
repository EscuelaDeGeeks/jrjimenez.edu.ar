"""Fix wp-content_* broken asset paths in HTML files."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://juanramonjimenez-pulgarin.com/"
BROKEN = re.compile(r"""wp-content_[a-z0-9_.@-]+""", re.I)

# Longest prefixes first (from mirror rewrite that replaced / with _)
PREFIX_MAP = [
    ("wp-content_plugins_elementor-pro_assets_css_", "wp-content/plugins/elementor-pro/assets/css/"),
    ("wp-content_plugins_elementor-pro_assets_js_", "wp-content/plugins/elementor-pro/assets/js/"),
    ("wp-content_plugins_elementor_assets_lib_", "wp-content/plugins/elementor/assets/lib/"),
    ("wp-content_plugins_elementor_assets_css_conditionals_", "wp-content/plugins/elementor/assets/css/conditionals/"),
    ("wp-content_plugins_elementor-pro_assets_css_conditionals_", "wp-content/plugins/elementor-pro/assets/css/conditionals/"),
    ("wp-content_plugins_elementor_assets_css_", "wp-content/plugins/elementor/assets/css/"),
    ("wp-content_plugins_elementor_assets_js_", "wp-content/plugins/elementor/assets/js/"),
    ("wp-content_plugins_bdthemes-element-pack_assets_css_", "wp-content/plugins/bdthemes-element-pack/assets/css/"),
    ("wp-content_plugins_bdthemes-element-pack_assets_js_common_", "wp-content/plugins/bdthemes-element-pack/assets/js/common/"),
    ("wp-content_plugins_bdthemes-element-pack_assets_js_modules_", "wp-content/plugins/bdthemes-element-pack/assets/js/modules/"),
    ("wp-content_plugins_bdthemes-element-pack_assets_js_", "wp-content/plugins/bdthemes-element-pack/assets/js/"),
    ("wp-content_plugins_bdthemes-prime-slider-lite_assets_css_", "wp-content/plugins/bdthemes-prime-slider-lite/assets/css/"),
    ("wp-content_plugins_bdthemes-prime-slider-lite_assets_js_", "wp-content/plugins/bdthemes-prime-slider-lite/assets/js/"),
    ("wp-content_plugins_ultimate-post-kit_assets_css_", "wp-content/plugins/ultimate-post-kit/assets/css/"),
    ("wp-content_plugins_ultimate-post-kit_assets_js_", "wp-content/plugins/ultimate-post-kit/assets/js/"),
    ("wp-content_themes_hello-elementor_assets_css_", "wp-content/themes/hello-elementor/assets/css/"),
    ("wp-content_themes_hello-elementor_assets_js_", "wp-content/themes/hello-elementor/assets/js/"),
    ("wp-content_uploads_elementor_google-fonts_css_", "wp-content/uploads/elementor/google-fonts/css/"),
    ("wp-content_uploads_elementor_google-fonts_fonts_", "wp-content/uploads/elementor/google-fonts/fonts/"),
    ("wp-content_uploads_elementor_css_", "wp-content/uploads/elementor/css/"),
    ("wp-content_uploads_", "wp-content/uploads/"),
    ("wp-includes_js_", "wp-includes/js/"),
]


def broken_to_url(token: str) -> str:
    rest = token
    query = ""
    if "@" in rest:
        rest, q = rest.split("@", 1)
        query = "?" + q
    for broken_prefix, real_prefix in PREFIX_MAP:
        if rest.startswith(broken_prefix):
            rest = real_prefix + rest[len(broken_prefix) :]
            break
    else:
        if rest.startswith("wp-content_"):
            rest = "wp-content/" + rest[len("wp-content_") :].replace("_", "/")
    return urljoin(BASE, rest + query)


def resolve_local(url: str) -> str | None:
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if parsed.query:
        p = Path(path)
        stem = f"{p.name}@{parsed.query.replace('/', '_')}"
        path = str(p.parent / stem) if str(p.parent) not in (".", "") else stem
    candidates = [ROOT / path, ROOT / f"{path}.css"]
    p = Path(path)
    if "@" in p.name:
        candidates.append(ROOT / p.parent / p.name.split("@", 1)[0])
    for cand in candidates:
        if cand.exists() and cand.stat().st_size > 0:
            return cand.relative_to(ROOT).as_posix()
    return None


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text
    for token in set(BROKEN.findall(text)):
        if not token.startswith("wp-content_"):
            continue
        url = broken_to_url(token)
        local = resolve_local(url)
        if local:
            rel = os.path.relpath(ROOT / local, path.parent).replace("\\", "/")
            text = text.replace(token, rel)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    n = 0
    for p in ROOT.rglob("*.html"):
        if any(x in p.parts for x in (".git", "scripts", "agent-tools")):
            continue
        if patch(p):
            n += 1
    print(f"repaired {n} files")


if __name__ == "__main__":
    main()