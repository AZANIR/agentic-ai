---
id: T3
title: "The NovaShop knowledge base with access-level metadata"
layer: "domain"
deps: []
acs: ["AC-01", "AC-05"]
files_hint: ["stages/s02_rag/data/"]
owner: "Contributor"
estimate: "S"
status: "todo"
---

# T3 — The NovaShop knowledge base with access-level metadata

## Why

A fixture and a subject of the lesson at once: it shows both how the search works and why the access filter is mandatory ([spec §6.1](../spec.md)).

## What

NovaShop policy and product-description files with an access-level flag in their own metadata. Mandatory: a document about the returns policy (the target of AC-01), one **internal** document that is close in meaning to a shopper's question (AC-05), one empty and one too short (AC-08b).

## Definition of Done

- [ ] There is a returns document that has to be found by a literal question
- [ ] There is an internal document that is the closest in meaning to a shopper's question
- [ ] There are an empty and a too-short file for checking the robustness of indexing
- [ ] Every document carries its access level in its metadata
- [ ] No personal data at all (spec §6.1)

## Notes

The internal document has to be genuinely the closest — otherwise AC-05 checks a coincidence rather than the filter.

Blocked by: —
