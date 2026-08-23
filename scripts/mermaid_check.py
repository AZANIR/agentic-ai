"""Валідація Mermaid-блоків у документі: типи, дужки, оголошені вузли й учасники."""

import re
import sys
from pathlib import Path

t = Path(sys.argv[1]).read_text(encoding="utf-8")
blocks = re.findall(r"```mermaid\n(.*?)```", t, re.S)
bad = []
for i, b in enumerate(blocks, 1):
    kind = b.strip().splitlines()[0].strip()
    if kind not in ("C4Context", "C4Container", "sequenceDiagram", "flowchart LR", "flowchart TD"):
        bad.append(f"блок {i}: невідомий тип {kind!r}")
    if "Bondary" in b:
        bad.append(f"блок {i}: друкарська помилка Container_Bondary")
    if b.count("(") != b.count(")"):
        bad.append(f"блок {i}: дужки не збалансовані")
    if "<placeholder>" in b:
        bad.append(f"блок {i}: заглушка")
    if kind.startswith("C4"):
        for pair in re.findall(r"Rel\((\w+), (\w+),", b):
            for node in pair:
                if not re.search(
                    rf"(Person|System|Container|System_Ext|Container_Boundary|System_Boundary)\w*\({node},",
                    b,
                ):
                    bad.append(f"блок {i}: Rel посилається на невизначений вузол {node!r}")
    if kind == "sequenceDiagram":
        # `actor` і `participant` рівноправні в Mermaid. Валідатор, який знає лише
        # половину синтаксису, оголошує справні діаграми зламаними — і це рівно та
        # сама вада, від якої він мав захищати, тільки в інший бік.
        declared = set(re.findall(r"(?:participant|actor) (\w+)", b))
        used = set(re.findall(r"^\s*(\w+)(?:->>|-->>)", b, re.M)) | set(
            re.findall(r"(?:->>|-->>)(\w+):", b)
        )
        if unknown := used - declared:
            bad.append(f"блок {i}: учасник не оголошений: {unknown}")

print(f"блоків: {len(blocks)}")
print("\n".join("ЗБІЙ · " + x for x in bad) if bad else "усі діаграми валідні")
sys.exit(1 if bad else 0)
