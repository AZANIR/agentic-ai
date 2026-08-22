---
id: T9
title: "Терміни етапу в глосарій, статус етапу в програму"
layer: "docs"
deps: ["T7"]
acs: []
files_hint: ["GLOSSARY.md", "CURRICULUM.md", "docs/architecture-map.md"]
owner: "Contributor"
estimate: "S"
status: "todo"
---

# T9 — Терміни етапу в глосарій, статус етапу в програму

## Why

Критерії завершеності етапу №7 і №8 у [CURRICULUM.md](../../../../CURRICULUM.md). Без цього наступні етапи вводять ті самі терміни заново.

## What

Перенести терміни з `sad.md` §12 у `GLOSSARY.md` (step, tool registry, guard, confirmation gate, scenario, rejection) і звірити 100% покриття термінів уроку. Оновити статус етапу 1 на ✅ у `CURRICULUM.md` і статус компонентів у README. Перезапустити `survey` у brownfield-режимі: карта має вказувати на реальні `file:line` замість посилань на спеку.

## Definition of Done

- [ ] Кожен виділений термін уроку має визначення в глосарії (KPI 100%)
- [ ] Статус етапу 1 оновлено в CURRICULUM.md і обох README
- [ ] Карта архітектури перезнята в brownfield-режимі
- [ ] Усі посилання резолвляться

## Notes

Остання задача етапу: закриває пункти 7 і 8 критеріїв завершеності.

Блокується: T7
