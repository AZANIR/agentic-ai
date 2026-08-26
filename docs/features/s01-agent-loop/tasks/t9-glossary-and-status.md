---
id: T9
title: "The stage's terms into the glossary, the stage's status into the curriculum"
layer: "docs"
deps: ["T7"]
acs: []
files_hint: ["GLOSSARY.md", "CURRICULUM.md", "docs/architecture-map.md"]
owner: "Contributor"
estimate: "S"
status: "todo"
---

# T9 — The stage's terms into the glossary, the stage's status into the curriculum

## Why

Stage completion criteria №7 and №8 in [CURRICULUM.md](../../../../CURRICULUM.md). Without this
the following stages introduce the same terms all over again.

## What

Move the terms from `sad.md` §12 into `GLOSSARY.md` (step, tool registry, guard, confirmation
gate, scenario, rejection) and reconcile 100% coverage of the lesson's terms. Update the status of
stage 1 to ✅ in `CURRICULUM.md` and the component statuses in the README. Re-run `survey` in
brownfield mode: the map has to point at real `file:line` locations instead of references to the
spec.

## Definition of Done

- [ ] Every highlighted term of the lesson has a glossary definition (KPI 100%)
- [ ] The status of stage 1 is updated in CURRICULUM.md and in both READMEs
- [ ] The architecture map is re-taken in brownfield mode
- [ ] All links resolve

## Notes

The stage's last task: it closes items 7 and 8 of the completion criteria.

Blocked by: T7
