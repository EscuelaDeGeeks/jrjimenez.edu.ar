"""Report broken relative asset references in HTML."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATTR = re.compile(
    r"""(?:href|src)=['"]([^'"]+\.(?:css|js|jpg|jpeg|png|gif|webp|svg|woff2?))['"]""",
    re.I,
)

missing: Counter[tuple[str, str]] = Counter()
for p in ROOT.rglob("*.html"):
    if ".git" in p.parts or "agent-tools" in p.parts:
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    for m in ATTR.finditer(text):
        ref = m.group(1).split("?")[0].split("#")[0]
        if ref.startswith(("http", "//", "data:", "mailto:", "#", "wp-json", "wp-admin")):
            continue
        if ref.startswith("/"):
            target = (ROOT / ref.lstrip("/")).resolve()
        else:
            target = (p.parent / ref).resolve()
        try:
            ok = target.is_file() and target.stat().st_size > 0
        except OSError:
            ok = False
        if not ok:
            missing[(ref, str(p.relative_to(ROOT)))] += 1

by_ref: Counter[str] = Counter()
for (ref, _page), n in missing.items():
    by_ref[ref] += n
print(f"broken refs: {sum(missing.values())} ({len(by_ref)} unique)")
for ref, n in by_ref.most_common(50):
    print(f"  {ref} ({n}x)")