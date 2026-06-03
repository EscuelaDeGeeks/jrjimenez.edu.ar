"""Point contact forms at the live WordPress site and update displayed email."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTACT_PAGE = "https://juanramonjimenez-pulgarin.com/contacto/"
AJAX = "https://juanramonjimenez-pulgarin.com/wp-admin/admin-ajax.php"
WP_ASSETS = "https://juanramonjimenez-pulgarin.com/wp-content/"
EMAIL_OLD = "i.juanramonjimenez@gmail.com"
EMAIL_NEW = "info@jrjimenez.edu.ar"

FILES = [ROOT / "contacto.html", ROOT / "contacto" / "index.html"]


def fetch_nonce() -> str | None:
    r = subprocess.run(
        ["curl", "-fsSL", CONTACT_PAGE],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    m = re.search(r'name="_wpnonce"\s+value="([^"]+)"', r.stdout)
    return m.group(1) if m else None


def patch(path: Path, nonce: str | None) -> None:
    text = path.read_text(encoding="utf-8")

    text = text.replace(EMAIL_OLD, EMAIL_NEW)

    text = re.sub(
        r'<form class="bdt-contact-form-form[^"]*"([^>]*?)action="[^"]*"',
        f'<form class="bdt-contact-form-form bdt-form-stacked bdt-grid bdt-grid-small without-recaptcha" data-bdt-grid="" action="{AJAX}"',
        text,
        count=1,
    )

    if nonce:
        text = re.sub(
            r'<input name="_wpnonce" value="[^"]*" type="hidden">',
            f'<input name="_wpnonce" value="{nonce}" type="hidden">',
            text,
            count=1,
        )

    if 'class="elementor-form" method="post"' in text and "action=" not in text.split("elementor-form")[1][:80]:
        text = text.replace(
            '<form class="elementor-form" method="post"',
            f'<form class="elementor-form" method="post" action="{CONTACT_PAGE}" enctype="multipart/form-data"',
            1,
        )
    else:
        text = re.sub(
            r'(<form class="elementor-form" method="post")(?: action="[^"]*")?(?: enctype="[^"]*")?',
            rf'\1 action="{CONTACT_PAGE}" enctype="multipart/form-data"',
            text,
            count=1,
        )

    text = text.replace('"ajaxurl":"wp-admin/admin-ajax.php"', f'"ajaxurl":"{AJAX}"')
    text = text.replace('"ajaxurl":"wp-admin\\/admin-ajax.php"', f'"ajaxurl":"{AJAX.replace("/", "\\/")}"')
    text = text.replace('"ajaxurl":"../wp-admin/admin-ajax.php"', f'"ajaxurl":"{AJAX}"')
    text = text.replace('"ajaxurl":"..\\/wp-admin\\/admin-ajax.php"', f'"ajaxurl":"{AJAX.replace("/", "\\/")}"')

    text = text.replace(
        '"urls":{"assets":"wp-content\\/plugins\\/elementor\\/assets\\/","ajaxurl":"'
        + AJAX.replace("/", "\\/")
        + '","uploadUrl":"wp-content\\/uploads"}',
        '"urls":{"assets":"'
        + WP_ASSETS.replace("/", "\\/")
        + 'plugins/elementor/assets/","ajaxurl":"'
        + AJAX.replace("/", "\\/")
        + '","uploadUrl":"'
        + WP_ASSETS.replace("/", "\\/")
        + 'uploads"}',
    )
    text = text.replace(
        '"urls":{"assets":"wp-content/plugins/elementor-pro/assets/","rest":"wp-json/"}',
        '"urls":{"assets":"'
        + WP_ASSETS
        + 'plugins/elementor-pro/assets/","rest":"https://juanramonjimenez-pulgarin.com/wp-json/"}',
    )

    path.write_text(text, encoding="utf-8")


def main() -> None:
    nonce = fetch_nonce()
    print(f"nonce: {nonce or '(unchanged)'}")
    for f in FILES:
        patch(f, nonce)
        print(f"patched {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()