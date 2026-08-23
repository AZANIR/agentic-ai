"""Валідація tasks.json: DAG, покриття критеріїв в обидва боки, DoD і files_hint."""

import json
import re
import sys
from pathlib import Path

slug = sys.argv[1]
base = Path(f"docs/features/{slug}")
d = json.loads((base / "tasks.json").read_text(encoding="utf-8"))
ids = {t["id"] for t in d["tasks"]}
bad = []

seen = set()


def visit(i, chain):
    if i in chain:
        bad.append("цикл: " + str(chain + [i]))
        return
    if i in seen:
        return
    task = next(t for t in d["tasks"] if t["id"] == i)
    for dep in task["deps"]:
        if dep not in ids:
            bad.append(f"{i} залежить від неіснуючого {dep}")
            continue
        visit(dep, chain + [i])
    seen.add(i)


for t in d["tasks"]:
    visit(t["id"], [])

spec = (base / "spec.md").read_text(encoding="utf-8")
spec_acs = {a for a, _ in re.findall(r"### (AC-\d+\w*) \((US-\d+)\)", spec)}
covered = {a for t in d["tasks"] for a in t["acs"]}
if spec_acs - covered:
    bad.append(f"AC без задачі: {sorted(spec_acs - covered)}")
if covered - spec_acs:
    bad.append(f"задача згадує неіснуючий AC: {sorted(covered - spec_acs)}")
for t in d["tasks"]:
    if not t.get("dod") or not t.get("files_hint"):
        bad.append(t["id"] + ": немає dod або files_hint")

par = [t["id"] for t in d["tasks"] if not t["deps"]]
print(f"задач: {len(ids)} | AC покрито: {len(covered)}/{len(spec_acs)} | паралельні старти: {par}")
print("\n".join("ЗБІЙ · " + b for b in bad) if bad else "tasks.json валідний в обидва напрямки")
sys.exit(1 if bad else 0)
