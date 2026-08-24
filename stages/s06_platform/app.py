"""Зшивання: воротарі -> гілка -> пам'ять -> агент -> трейс.

Тут п'ять етапів стають одним сервісом, і найважливіше в цьому файлі — те, чого в ньому
**немає**: жодної правки в етапах 1–5. Якщо зшивання вимагає щось там підправити, значить межа
між етапами була проведена не там, і це привід для ADR, а не для тихого патча (C-1).

**Порядок кроків трейсу — і є відповідь на «чому».** Спершу вердикт воротарів, потім гілка,
потім що взято з пам'яті й що відкинуто, і лише тоді робота агента. Трейс, у якому гілка стоїть
після відповіді, не пояснює нічого: він переказує те, що вже сталося.

**Межа трейсу названа наперед (ADR-0005).** Етапи 2 і 5 не пишуть у трейс жодного кроку, тож
цей трейс відповідає на «яка гілка» і **не** відповідає на «чому знайдено саме ці документи».
Причини відкидання фактів існують у `Context.skipped` — сервіс переносить їх у свій крок, бо це
його рішення, а не етапу 5.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from shared.counters import Counters
from shared.factstore import FactStore
from stages.s01_agent_loop.loop import run_agent
from stages.s02_rag.documents import PUBLIC
from stages.s03_router.graph import run_graph
from stages.s05_memory.facts import Fact
from stages.s06_platform.guards import OK, Verdict, admit, charge
from stages.s06_platform.intent import MATH, ORDERS, classify
from stages.s06_platform.observe import Metrics

# Оцінка вартості одного запиту. Не рахунок провайдера — запобіжник має спрацювати раніше за
# катастрофу, а не звести баланс (spec §5, «чого план не доводить»).
COST_PER_REQUEST = 0.01

# Четвертий рід результату поруч із трьома відмовами воротарів. Він не про клієнта —
# він про сервіс, і саме тому має своє імʼя в метриках: оператор, що бачить сплеск
# `dependency_down`, іде дивитись на стан, а не на клієнтів.
DEPENDENCY_DOWN = "dependency_down"


@dataclass
class Answer:
    """Що сервіс віддає назовні. Ключа тут немає й бути не може."""

    ok: bool
    text: str = ""
    kind: str = OK
    trace_id: str = ""
    branch: str = ""
    retry_after: float | None = None
    facts_used: list[str] = field(default_factory=list)


@dataclass
class Service:
    """Сервіс. Усі залежності передаються ззовні — тестується без мережі й без контейнерів."""

    settings: Any
    counters: Counters
    store: FactStore
    tracer: Any
    client: Any
    metrics: Metrics = field(default_factory=Metrics)

    def ask(self, key: str, question: str, *, now: float | None = None) -> Answer:
        """Один запит від початку до кінця."""
        now = time.time() if now is None else now
        trace_id = uuid.uuid4().hex[:12]

        verdict = admit(key, self.counters, self.settings, now=now)
        self.tracer.step(
            "guard",
            trace_ref=trace_id,
            verdict=verdict.kind,
            owner=verdict.owner,
            reason=verdict.reason,
        )
        if not verdict.allowed:
            return self._refused(verdict, trace_id)

        try:
            return self._answer(verdict, question, trace_id=trace_id, now=now)
        except Exception as error:  # noqa: BLE001 — межа сервісу: далі летіти нікуди
            # Один запит гірший за всі запити. Сховище, що впало, не має забирати із
            # собою процес: решта запитів може не торкатись його зовсім, а стан скаже
            # монітору правду раніше, ніж це помітить користувач.
            self.tracer.step("failed", trace_ref=trace_id, cause=type(error).__name__)
            self.metrics.request(DEPENDENCY_DOWN)
            return Answer(
                ok=False,
                kind=DEPENDENCY_DOWN,
                text=f"залежність недоступна: {type(error).__name__}",
                trace_id=trace_id,
            )

    def _refused(self, verdict: Verdict, trace_id: str) -> Answer:
        """Відмова коштує нуль викликів моделі — у цьому вся суть воротарів."""
        self.metrics.request(verdict.kind)
        return Answer(
            ok=False,
            kind=verdict.kind,
            text=verdict.reason,
            trace_id=trace_id,
            retry_after=verdict.retry_after,
        )

    def _answer(self, verdict: Verdict, question: str, *, trace_id: str, now: float) -> Answer:
        owner = verdict.owner
        intent = classify(question, client=self.client)
        self.tracer.step("intent", trace_ref=trace_id, **intent.as_step())

        context = self.store.context_for(owner, question, now=now)
        self.tracer.step(
            "memory",
            trace_ref=trace_id,
            taken=[fact["topic"] for fact in context.facts],
            # Причини відкидання переносить сервіс: етап 5 їх повертає, але у трейс не пише.
            skipped=[f"{skip.text}: {skip.reason}" for skip in context.skipped],
        )

        text = self._work(intent.branch, question, context.as_prompt(), trace_id=trace_id)

        spent = charge(owner, self.counters, COST_PER_REQUEST, now=now)
        self.tracer.step("done", trace_ref=trace_id, branch=intent.branch, spent=spent)
        self.metrics.request(OK)
        self.metrics.trace_written()

        self._remember(owner, question, now=now)
        return Answer(
            ok=True,
            text=text,
            trace_id=trace_id,
            branch=intent.branch,
            facts_used=[fact["text"] for fact in context.facts],
        )

    def _work(self, branch: str, question: str, memory: str, *, trace_id: str) -> str:
        """Гілка обирає, ЯКИЙ етап робить роботу. Жоден із них про сервіс не знає."""
        asked = f"{memory}\n\n{question}" if memory else question
        if branch in (ORDERS, MATH):
            state = run_graph(asked, access=PUBLIC, client=self.client, tracer=self.tracer)
            return state.answer
        result = run_agent(asked, client=self.client, tracer=self.tracer)
        return result.answer

    def _remember(self, owner: str, question: str, *, now: float) -> None:
        """Питання стає фактом лише тоді, коли воно про співрозмовника (чекліст етапу 5)."""
        if not question.lower().startswith(("запамʼятай", "запам'ятай")):
            return
        self.store.remember(Fact(owner=owner, topic="note", text=question, stored_at=now))
