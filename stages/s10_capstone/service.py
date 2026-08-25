"""Зібраний сервіс: воротарі етапу 6, робота крізь перехідники (AC-01, AC-07).

Тут немає власного циклу агента, власного пошуку, власної пам'яті й власних воротарів. Кожен
такий модуль означав би, що відповідну частину **не вдалося** зібрати, — і це мало б стояти у
звіті, а не в коді.

**Складання йде згори вниз.** Сервіс кличе частини; частини про сервіс не знають. Зворотний
напрямок вимагав би змінювати частини, що заборонено (C-2).

**Відповідь називає, хто працював.** Не заради оздоби: без цього «сервіс відповів» не
відрізняється від «одна частина відповіла за всіх», а саме це й треба бачити.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shared.counters import Counters
from stages.s05_memory.decision import decide
from stages.s06_platform.guards import OK, Verdict, admit, charge
from stages.s06_platform.observe import Metrics
from stages.s10_capstone import seams

# Ціна одного запиту для бюджетного запобіжника. Число етапу 6; капстоун його не переглядає.
COST_PER_REQUEST = 0.01

SEARCH = "search"
AGENT = "agent"
ROUTED = "routed"


@dataclass(frozen=True)
class Reply:
    """Відповідь сервісу. Імʼя **не** `Answer` навмисно: два різні `Answer` вже є в курсі.

    Етап 2 і етап 6 обидва мають клас `Answer`, і це різні класи (шов `answer_of_search`).
    Третій із тим самим іменем зробив би плутанину не незручністю, а помилкою на рівному
    місці.
    """

    ok: bool
    text: str
    kind: str = OK
    branch: str = ""
    trace_id: str = ""
    parts: tuple[str, ...] = field(default_factory=tuple)
    detail: str = ""


def _branch(question: str) -> str:
    """Яка частина робитиме роботу. Груба евристика — і названа грубою.

    Класифікатор етапу 6 сюди не їде: він кличе модель, а гілка тут потрібна **до** будь-якого
    виклику, щоб пошук устиг віддати контекст. Це рішення капстоуна, і воно стоїть у розділі
    власних рішень `ARCHITECTURE.md` разом із причиною.
    """
    lowered = question.lower()
    if any(word in lowered for word in ("поверн", "гарант", "достав", "оплат")):
        return SEARCH
    if any(word in lowered for word in ("замовлен", "статус", "де мо")):
        return ROUTED
    return AGENT


@dataclass
class Capstone:
    """Складений сервіс. Усі залежності подаються ззовні — як на етапі 6."""

    settings: Any
    counters: Counters
    client: Any
    tracer: Any
    memory_path: Path
    metrics: Metrics = field(default_factory=Metrics)
    base: Any = None

    def __post_init__(self) -> None:
        # Індекс будується раз, на старті: шов `knowledge_base_needs_building`.
        self.base = self.base or seams.build_search()
        self.memory = seams.open_memory(self.memory_path)

    def ask(self, key: str, question: str, *, now: float | None = None) -> Reply:
        """Один запит від початку до кінця."""
        now = time.time() if now is None else now
        trace_id = uuid.uuid4().hex[:12]
        self.tracer.step("received", trace_ref=trace_id, chars=len(question))

        verdict = admit(key, self.counters, self.settings, now=now)
        self.tracer.step("guard", trace_ref=trace_id, verdict=verdict.kind, owner=verdict.owner)
        if not verdict.allowed:
            return self._refused(verdict, trace_id)

        try:
            return self._work(verdict, question, trace_id=trace_id, now=now)
        except Exception as error:  # noqa: BLE001 — межа сервісу: далі летіти нікуди
            # Відмова ЧАСТИНИ не є падінням системи — урок етапу 4. Сервіс лишається
            # живим, а у відповіді названо, що саме відмовило.
            self.tracer.step("failed", trace_ref=trace_id, cause=type(error).__name__)
            self.metrics.request("dependency_down")
            return Reply(
                ok=False,
                text=f"частина відмовила: {type(error).__name__}",
                kind="dependency_down",
                trace_id=trace_id,
                detail=type(error).__name__,
            )

    def _refused(self, verdict: Verdict, trace_id: str) -> Reply:
        """Відмова коштує нуль викликів моделі — уся суть воротарів етапу 6."""
        self.metrics.request(verdict.kind)
        return Reply(ok=False, text=verdict.reason, kind=verdict.kind, trace_id=trace_id)

    def _work(self, verdict: Verdict, question: str, *, trace_id: str, now: float) -> Reply:
        branch = _branch(question)
        parts: list[str] = ["s06"]

        context = seams.from_search(self.base, question, tracer=self.tracer)
        parts.append(context.part)
        asked = f"{context.text}\n\n{question}" if context.text else question

        if branch == SEARCH and context.text:
            worked = context
        elif branch == ROUTED:
            worked = seams.from_graph(asked, client=self.client, tracer=self.tracer)
        else:
            worked = seams.from_agent(asked, client=self.client, tracer=self.tracer)
        if worked.part not in parts:
            parts.append(worked.part)

        spent = charge(verdict.owner, self.counters, COST_PER_REQUEST, now=now)
        self.metrics.spend(COST_PER_REQUEST)
        self.metrics.request(OK)

        kept = decide(seams.classify(question))
        if kept.keep:
            seams.remember(self.memory, verdict.owner, question, now=now)
            parts.append("s05")
        self.tracer.step(
            "done", trace_ref=trace_id, branch=branch, spent=spent, kept=kept.keep, parts=parts
        )
        return Reply(
            ok=True,
            text=worked.text,
            branch=branch,
            trace_id=trace_id,
            parts=tuple(parts),
            detail=worked.detail,
        )
