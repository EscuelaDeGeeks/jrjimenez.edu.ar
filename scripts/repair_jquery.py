from pathlib import Path

root = Path(__file__).resolve().parent.parent

# script id -> local path (query string stored as @ver=)
SCRIPT_PATHS = {
    "jquery-core-js": "wp-includes/js/jquery/jquery.min.js@ver=3.7.1",
    "jquery-migrate-js": "wp-includes/js/jquery/jquery-migrate.min.js@ver=3.4.1",
    "jquery-ui-core-js": "wp-includes/js/jquery/ui/core.min.js@ver=1.13.3",
    "imagesloaded-js": "wp-includes/js/imagesloaded.min.js@ver=5.0.0",
    "wp-hooks-js": "wp-includes/js/dist/hooks.min.js@ver=7496969728ca0f95732d",
    "wp-i18n-js": "wp-includes/js/dist/i18n.min.js@ver=781d11515ad3d91786ec",
}

DOWNLOADS = {
    "wp-includes/js/jquery/ui/core.min.js@ver=1.13.3": "https://juanramonjimenez-pulgarin.com/wp-includes/js/jquery/ui/core.min.js?ver=1.13.3",
    "wp-includes/js/imagesloaded.min.js@ver=5.0.0": "https://juanramonjimenez-pulgarin.com/wp-includes/js/imagesloaded.min.js?ver=5.0.0",
}

fixes = [
    (
        f'<script id="{sid}" src="wp-includes/"></script>',
        f'<script id="{sid}" src="{path}"></script>',
    )
    for sid, path in SCRIPT_PATHS.items()
]

import subprocess

for rel, url in DOWNLOADS.items():
    dest = root / rel
    if dest.exists() and dest.stat().st_size > 0:
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-fsSL", "-o", str(dest), url], check=False)
    print(f"downloaded {rel}")

count = 0
for p in root.rglob("*.html"):
    if ".git" in p.parts or "scripts" in p.parts:
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    original = text
    for old, new in fixes:
        text = text.replace(old, new)
    if text != original:
        p.write_text(text, encoding="utf-8")
        count += 1
print(f"fixed {count} files")