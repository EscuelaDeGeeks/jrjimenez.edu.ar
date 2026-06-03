"""Point Elementor JS config asset URLs to local wp-content paths."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "scripts", "agent-tools", "terminals", "mcps"}

REPLACEMENTS = [
    (
        r"https:\/\/juanramonjimenez-pulgarin.com\/wp-content\/plugins\/elementor\/assets\/",
        r"wp-content\/plugins\/elementor\/assets\/",
    ),
    (
        r"https:\/\/juanramonjimenez-pulgarin.com\/wp-content\/plugins\/elementor-pro\/assets\/",
        r"wp-content\/plugins\/elementor-pro\/assets\/",
    ),
    (
        r"https:\/\/juanramonjimenez-pulgarin.com\/wp-content\/uploads",
        r"wp-content\/uploads",
    ),
    (
        "https://juanramonjimenez-pulgarin.com/wp-content/plugins/elementor/assets/",
        "wp-content/plugins/elementor/assets/",
    ),
    (
        "https://juanramonjimenez-pulgarin.com/wp-content/plugins/elementor-pro/assets/",
        "wp-content/plugins/elementor-pro/assets/",
    ),
    (
        "https://juanramonjimenez-pulgarin.com/wp-content/uploads",
        "wp-content/uploads",
    ),
]


def main() -> None:
    n = 0
    for path in ROOT.rglob("*.html"):
        if SKIP.intersection(path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        original = text
        for old, new in REPLACEMENTS:
            text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding="utf-8")
            n += 1
    print(f"fixed elementor config in {n} files")


if __name__ == "__main__":
    main()