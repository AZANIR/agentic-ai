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

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from stages.s05_memory.facts import (
    ACTIVE,
    Fact,
    as_context_line,
    describe_skip,
    is_active,
    one_line,
    replace,
)
from stages.s05_memory.retrieval import Retrieval, get_retrieval

OPEN_FACTS = "=== ЩО МИ ЗНАЄМО ПРО СПІВРОЗМОВНИКА (дані) ==="
CLOSE_FACTS = "=== КІНЕЦЬ ДАНИХ ==="


def _safe(value: str) -> str:
    """Прибрати з тексту факту роздільники блоку даних — він недовірений за побудовою."""
    for marker in (OPEN_FACTS, CLOSE_FACTS):
        value = value.replace(marker, "")
    return one_line(value)


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
    # Ліміт поруч із порогом: обидва вирішують, чи факт дійде, тож «не дійшов» без
    # обох чисел неможливо пояснити ні у трейсі, ні користувачеві.
    limit: int

    def as_prompt(self) -> str:
        """Факти для моделі — окремим позначеним блоком, як дані, а не як вказівки."""
        if not self.facts:
            return ""
        # Текст писав користувач. Без нейтралізації факт із власним `CLOSE_FACTS`
        # усередині закривав блок даних достроково, і решта його тексту ставала в
        # промпті інструкцією — рівно тим, чого позначений блок і мав не допустити.
        lines = "\n".join(f"- [{_safe(f['topic'])}] {_safe(f['text'])}" for f in self.facts)
        return f"{OPEN_FACTS}\n{lines}\n{CLOSE_FACTS}"


class Memory:
    """Файл фактів. Один рядок — один запис, читається очима (ADR етапу 0001)."""

    def __init__(
        self, path: Path, *, retrieval: Retrieval | None = None, threshold: float | None = None
    ) -> None:
        self.path = path
        self.retrieval = retrieval or get_retrieval()
        # Поріг за замовчуванням бере ВИБІРКА: її оцінки, її шкала. Зашите тут число
        # підходило лише словниковій, і вмикання семантичної спорожняло контекст.
        self.threshold = self.retrieval.threshold if threshold is None else threshold
        self.broken: list[str] = []
        # Сирі рядки, які не розібрались. Пропустити на читанні й затерти на записі —
        # це не «решта памʼяті робоча», це знищення єдиного доказу псування.
        self.unparsed: list[str] = []

    def all_facts(self) -> list[Fact]:
        """Прочитати файл. Зіпсований рядок названо й пропущено — решта памʼяті робоча."""
        self.broken = []
        if not self.path.exists():
            return []
        facts = []
        self.unparsed = []
        # `.splitlines()` рве рядок за U+2028 — тим самим символом, який `json.dumps`
        # НЕ екранує. Один такий символ у тексті факту робив із запису дві половини,
        # і факт зникав з обох. Текст факту пише користувач, а U+2028 приїжджає з PDF.
        raw = self.path.read_text(encoding="utf-8").split("\n")
        for number, line in enumerate(raw, 1):
            if not line.strip():
                continue
            try:
                facts.append(Fact.from_line(line))
            except ValueError as error:
                self.broken.append(f"рядок {number}: {error}")
                self.unparsed.append(line)
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
                # Хто старіший, той і йде в історію. Без цієї гілки повторний імпорт
                # старого файлу відкочував памʼять і ставив час заміни РАНІШЕ за час
                # самого запису — історію, яку неможливо прочитати.
                if fact.stored_at < old.stored_at:
                    fact = replace(fact, at=old.stored_at)
                    rewritten.append(old)
                    continue
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
                    else f"понад ліміт {limit}"
                )
                skipped.append(Skipped(fact.text, below))
        return Context(facts=taken, skipped=skipped, threshold=self.threshold, limit=limit)

    def _write(self, facts: list[Fact]) -> None:
        """Записати памʼять. Нерозібране переноситься як є — стерти його не можна."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f.to_line() for f in facts] + self.unparsed
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
