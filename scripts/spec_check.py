"""Structural self-check специфікації: обидва напрямки, бо один пропускає діри."""

import re
import sys
from pathlib import Path

slug = sys.argv[1]
t = Path(f"docs/features/{slug}/spec.md").read_text(encoding="utf-8")
bad = []

ac_block = t[t.index("## 5. Acceptance criteria") : t.index("## 6. Non-functional")]
for pattern, why in [
    (r"\b(GET|POST|PUT|DELETE|PATCH)\b", "HTTP-дієслово"),
    (r"\b(200|201|400|401|403|404|500)\b", "код статусу"),
    (r"\bSELECT\b|\bINSERT\b", "SQL"),
    (r"[a-z_]+\.[a-z_]+_error", "код помилки"),
]:
    if re.search(pattern, ac_block):
        bad.append(f"заборонений токен у AC: {why}")

us = re.findall(r"### (US-\d+):", t)
acs = re.findall(r"### (AC-\d+\w*) \((US-\d+)\)", t)
types = set(re.findall(r"### AC-\d+\w* \(US-\d+\) — (.+)", t))
covered = {u for _, u in acs}
if missing := [u for u in us if u not in covered]:
    bad.append(f"US без жодного AC: {missing}")
need = {"happy path", "error", "authorization", "domain invariant", "cross-context"}
if not need <= types:
    bad.append(f"немає типів покриття: {need - types}")

spec_acs = {a for a, _ in acs}
rows = set(re.findall(r"^\| (AC-[\w-]+) \|", t, re.M))
if spec_acs - rows:
    bad.append(f"AC без рядка в плані тестів: {spec_acs - rows}")
if rows - spec_acs:
    bad.append(f"рядок плану без AC у §5: {rows - spec_acs}")

for section in (
    "## 6.1 Security",
    "### Чого цей план свідомо не доводить",
    "### Прийняті припущення",
):
    if section not in t:
        bad.append(f"немає розділу: {section}")

print(f"US: {len(us)} | AC: {len(acs)} | рядків покриття: {len(rows)} | типи: {len(types)}")
print("\n".join("ЗБІЙ · " + b for b in bad) if bad else "self-check чистий в обидва напрямки")
