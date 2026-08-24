"""Довготривала памʼять: витягти, зберегти, дістати потрібне — і не дістати зайвого.

Три дії, і третя найважча. Витягти факт із розмови й записати його у файл — це двадцять
рядків. Дістати **саме те, що стосується питання**, і не дістати решти — це те, заради чого
етап існує:

> Показати, що факт зберігся, легко. Показати, що нерелевантний факт **не** дійшов, —
> власне робота.

**Чотири умови, за яких факт потрапляє у контекст**, і жодну не можна пропустити:

    власник     фільтр стоїть ДО відбору top-k (ADR етапу 0004)
    статус      замінений факт не повертається ніколи
    термін      протухле не бере участі (ADR етапу 0003)
    поріг       релевантність вища за межу, і кількість обмежена

Порядок фільтра за власником — не деталь реалізації. Постав його після відбору, і чужий
факт займе слот у видачі, потім його приберуть — і **власний факт, який мав дійти, зникне**.
Витоку немає; відповідь зникла. Це дослівно та сама вада, що на етапі 2 з документами, і
саме тому перевірок дві: чуже не дійшло **і** своє дійшло.

**Текст факту недовірений.** Його писав користувач у розмові, і в промпт він іде як дані, у
позначеному блоці — тим самим патерном, що знайдені документи на етапі 2. Факт «запамʼятай:
ігноруй попередні інструкції» зберігається як звичайний факт і не змінює нічого.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.llm import get_model
from stages.s05_memory.facts import ACTIVE, Fact, as_context_line, describe_skip, is_active, replace
from stages.s05_memory.retrieval import Retrieval, get_retrieval

OPEN_FACTS = "=== ЩО МИ ЗНАЄМО ПРО СПІВРОЗМОВНИКА (дані) ==="
CLOSE_FACTS = "=== КІНЕЦЬ ДАНИХ ==="

_EXTRACT = """Витягни з розмови факти, які варто памʼятати про співрозмовника надовго.

Поверни JSON-масив обʼєктів із полями `topic` і `text`. Тема — одне слово про що факт
(`name`, `address`, `preference`). Якщо памʼятати нічого — поверни порожній масив.

{lines}"""


@dataclass
class Skipped:
    """Факт, який не дійшов, і чому. Причина потрібна: інакше памʼять просто «забула»."""

    text: str
    reason: str


@dataclass
class Context:
    """Що пішло в промпт і що лишилось за бортом."""

    facts: list[dict[str, Any]]
    skipped: list[Skipped]
    threshold: float

    def as_prompt(self) -> str:
        """Факти для моделі — окремим позначеним блоком, як дані, а не як вказівки."""
        if not self.facts:
            return ""
        lines = "\n".join(f"- [{f['topic']}] {f['text']}" for f in self.facts)
        return f"{OPEN_FACTS}\n{lines}\n{CLOSE_FACTS}"


class Memory:
    """Файл фактів. Один рядок — один запис, читається очима (ADR етапу 0001)."""

    def __init__(
        self, path: Path, *, retrieval: Retrieval | None = None, threshold: float = 0.3
    ) -> None:
        self.path = path
        self.retrieval = retrieval or get_retrieval()
        self.threshold = threshold
        self.broken: list[str] = []

    def all_facts(self) -> list[Fact]:
        """Прочитати файл. Зіпсований рядок названо й пропущено — решта памʼяті робоча."""
        self.broken = []
        if not self.path.exists():
            return []
        facts = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                facts.append(Fact.from_line(line))
            except ValueError as error:
                self.broken.append(f"рядок {number}: {error}")
        return facts

    def remember(self, fact: Fact) -> Fact | None:
        """Зберегти факт. Новіший факт тієї ж теми того ж власника замінює старий.

        Повертає замінений факт, якщо заміна сталася, — щоб виклик міг це показати.
        """
        existing = self.all_facts()
        retired = None
        rewritten = []
        for old in existing:
            same_topic = old.owner == fact.owner and old.topic == fact.topic
            if same_topic and old.status == ACTIVE:
                retired = replace(old, at=fact.stored_at)
                rewritten.append(retired)
            else:
                rewritten.append(old)
        rewritten.append(fact)
        self._write(rewritten)
        return retired

    def context_for(self, owner: str, question: str, *, now: float, limit: int = 3) -> Context:
        """Факти для промпту. Чотири умови, і фільтр власника — перша з них."""
        # ДО відбору. Після — чужий факт зайняв би слот, і власний зник би з видачі.
        mine = [f for f in self.all_facts() if f.owner == owner]

        skipped, alive = [], []
        for fact in mine:
            reason = describe_skip(fact, now=now)
            if reason or not is_active(fact, now=now):
                skipped.append(Skipped(fact.text, reason or "неактивний"))
            else:
                alive.append(fact)

        scores = self.retrieval.score(question, [f.text for f in alive])
        ranked = sorted(zip(scores, alive, strict=True), key=lambda pair: pair[0], reverse=True)

        taken = []
        for score, fact in ranked:
            if score >= self.threshold and len(taken) < limit:
                taken.append(as_context_line(fact))
            else:
                below = (
                    f"оцінка {score:.2f} < {self.threshold}"
                    if score < self.threshold
                    else "понад ліміт"
                )
                skipped.append(Skipped(fact.text, below))
        return Context(facts=taken, skipped=skipped, threshold=self.threshold)

    def _write(self, facts: list[Fact]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(f.to_line() for f in facts) + "\n", encoding="utf-8")


def extract(
    conversation: list[dict[str, str]], *, client: Any, model: str | None = None
) -> list[dict[str, str]]:
    """Спитати модель, що з розмови варто памʼятати. Порожній перелік — нормальна відповідь."""
    lines = "\n".join(f"- {m['role']}: {m['content']}" for m in conversation)
    reply = client.chat.completions.create(
        model=model or get_model(),
        messages=[{"role": "user", "content": _EXTRACT.format(lines=lines)}],
    )
    raw = (reply.choices[0].message.content or "").strip()
    try:
        found = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(found, list):
        return []
    return [
        {"topic": str(item["topic"]), "text": str(item["text"])}
        for item in found
        if isinstance(item, dict) and item.get("topic") and item.get("text")
    ]
