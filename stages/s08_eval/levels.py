"""Три рівні оцінювання — три **незалежні** вердикти, ніколи не один бал (ADR-0003).

Правило приписування дефекта рівню одне, і воно однозначне:

    e2e         про ОСТАННЮ відповідь і ні про що інше
    траєкторія  про ПОСЛІДОВНІСТЬ кроків: порядок, кількість, зайві виклики
    компонент   про ОДИН крок і його власний результат: відмовив, відхилив, не знайшов

Один кейс може провалити два рівні — це не подвійний облік, а два різні факти. Агент, що
покликав не той інструмент і отримав відмову, має **і** хибний шлях, **і** зламаний крок;
читач має бачити обидва.

**Порожній рівень — «не оцінено», не «пройдено»** (ADR-0006). Трейс без кроків потрібного
виду не доводить справності: він доводить, що дивитись нема на що. Рівень, який зараховує
відсутність даних як успіх, показує тим зеленіший звіт, чим бідніший трейс.

**Вид оцінювача — поле, а не домовленість** (ADR-0004). Він друкується поруч із вердиктом, і
набір стверджує, що детермінований оцінювач не покликав суддю **жодного разу**.
"""

from __future__ import annotations

from dataclasses import dataclass

from stages.s08_eval.cases import Case
from stages.s08_eval.judge import Judge, Unavailable
from stages.s08_eval.trajectory import FRAME, Trajectory

PASSED = "пройдено"
FAILED = "провалено"
UNSCORED = "не оцінено"

DETERMINISTIC = "детермінований"
JUDGED = "судить"

E2E = "e2e"
PATH = "траєкторія"
COMPONENT = "компонент"

# Бал, від якого відповідь вважається такою, що виконала задачу. Ціле число за шкалою
# `judge.SCALE`, назване тут: поріг, схований у коді, — це думка, яку ніхто не обговорював.
PASS_SCORE = 2

# Кроки, що є **роботою** підсистем. Якщо в траєкторії немає жодного, компонентний рівень
# не має на що дивитись.
COMPONENT_KINDS = frozenset(
    {
        "tool_call",
        "tool_error",
        "tool_rejected",
        "tool_unknown",
        "mcp_call",
        "search",
        "memory",
        "route",
        "llm_call",
        "refused",
    }
)

# Кроки, що є **відмовою** окремої підсистеми.
BROKEN_KINDS = frozenset(
    {
        "tool_error",
        "tool_rejected",
        "tool_unknown",
        "step_blocked",
        "specialist_failed",
        # Ліміт прогону — це запобіжник, який СПРАЦЮВАВ. Приписати його траєкторії
        # («забагато кроків») означало б звинуватити шлях у тому, що зупинив його
        # інший механізм.
        "run_limit",
    }
)


@dataclass(frozen=True)
class Verdict:
    """Один вердикт одного рівня. `kind` друкується поруч — це вимога, не оздоба."""

    level: str
    state: str
    kind: str
    reason: str


def e2e(case: Case, trajectory: Trajectory, judge: Judge) -> Verdict:
    """Чи виконано задачу. **Судить** — бо «виконано» не є порівнянням рядків.

    Відповідь береться з **трейсу**, а не з опису кейса. Різниця не косметична: суддя, що
    читає опис, виносить вердикт про те, що агент мав сказати, а не про те, що він сказав.
    Перша редакція робила саме так — і кейс, у якого з трейсу прибрали крок відповіді,
    діставав «пройдено, бал 3». Перевірка «та сама відповідь, різні шляхи» при цьому
    порівнювала один рядок сам із собою: тотожність, яку неможливо порушити.

    Відповіді в трейсі немає взагалі — **не оцінено**, симетрично до компонентного рівня:
    дивитись нема на що, і зараховувати це успіхом означало б робити звіт тим зеленішим,
    чим бідніший трейс.
    """
    said = trajectory.answer()
    if said is None:
        return Verdict(E2E, UNSCORED, JUDGED, "відповіді в трейсі немає")
    try:
        scored = judge.score(case.task, said, case.expected_answer)
    except Unavailable as error:
        return Verdict(E2E, UNSCORED, JUDGED, str(error))
    state = PASSED if scored.score >= PASS_SCORE else FAILED
    return Verdict(E2E, state, JUDGED, f"бал {scored.score}, поріг {PASS_SCORE}")


def path(case: Case, trajectory: Trajectory) -> Verdict:
    """Чи розумний шлях. **Детермінований** — послідовність порівнюється, а не оцінюється."""
    tools = tuple(trajectory.tools())
    if tools != case.expected_tools:
        return Verdict(
            PATH,
            FAILED,
            DETERMINISTIC,
            f"шлях {list(tools)} замість {list(case.expected_tools)}",
        )
    if trajectory.length > case.budget:
        return Verdict(
            PATH, FAILED, DETERMINISTIC, f"кроків {trajectory.length}, бюджет {case.budget}"
        )
    return Verdict(PATH, PASSED, DETERMINISTIC, f"{trajectory.length} кроків у бюджеті")


def component(case: Case, trajectory: Trajectory) -> Verdict:
    """Який саме крок зламався. **Детермінований** — крок або відмовив, або ні."""
    seen = [step for step in trajectory.steps if step["kind"] in COMPONENT_KINDS]
    if not seen:
        # Не «пройдено»: дивитись нема на що. Саме цей стан і показує, чого бракує у
        # трейсах сервісу етапу 6 — виклику моделі там немає жодного (ADR-0008).
        return Verdict(COMPONENT, UNSCORED, DETERMINISTIC, "кроків підсистем у трейсі немає")
    broken = [step for step in trajectory.steps if step["kind"] in BROKEN_KINDS]
    if broken:
        first = broken[0]
        # Номер — позиція в ТРАЄКТОРІЇ, а не наскрізний `seq` дописувача. На трейсі сервісу
        # `seq` глобальний на процес, тож другий крок третього запиту звався «крок 9», а
        # рівень траєкторії поруч рахував кроки вже без обрамлення.
        worked = [step for step in trajectory.steps if step["kind"] not in FRAME]
        where = worked.index(first) + 1 if first in worked else 0
        # Друкується **імʼя** поля, а не вільний текст. `reason` пише людина або сервіс, і
        # на живому трафіку він переніс би написане користувачем просто у звіт (AC-07b).
        named = next((f" · {first[name]}" for name in ("tool", "node") if name in first), "")
        return Verdict(COMPONENT, FAILED, DETERMINISTIC, f"крок {where} · {first['kind']}{named}")
    return Verdict(COMPONENT, PASSED, DETERMINISTIC, f"{len(seen)} кроків без відмов")


def evaluate(case: Case, trajectory: Trajectory, judge: Judge) -> list[Verdict]:
    """Три вердикти. Порядок сталий: e2e, траєкторія, компонент."""
    return [
        e2e(case, trajectory, judge),
        path(case, trajectory),
        component(case, trajectory),
    ]
