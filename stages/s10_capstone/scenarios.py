"""Шість наскрізних сценаріїв: гілка **і** фінальний стан (ADR-0006).

Найпростіше звіряти відповідь: текст правильний — отже все добре. Цей курс уже двічі показав,
чому цього замало. Етап 8 ловив агента, що дав правильну відповідь хибним шляхом; етап 6 ловив
сервіс, що відповідав і **клав пароль у пам'ять**. В обох випадках текст був бездоганний.

Складання додає третю причину: частина може не спрацювати, а відповідь усе одно вийде
правдоподібною — бо її дасть інша частина.

Тому кожен сценарій фіксує **чотири** речі: гілку, склад частин, що працювали, покликані
інструменти й фінальний стан — що лишилось у пам'яті. Останній сценарій навмисно **ламає
частину**: сервіс має лишитись живим, назвати, що саме відмовило, і перелічити тих, хто вже
встиг відпрацювати.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shared.config import Settings
from shared.counters import InMemory
from shared.fake_llm import FakeLLM, text, tool_call
from stages.s10_capstone.service import AGENT, ROUTED, SEARCH, Capstone

NOW = 1_700_000_000.0
KEY = "demo-key-0001"
STRANGER = "not-a-key"


def demo_settings(**kwargs: Any) -> Settings:
    """Налаштування демо — той самий спосіб, що в етапу 6: ключі подаються явно.

    Це не перехідник: `Settings` — спільний тип, і етап 6 будує його так само. Дублювання
    трьох рядків дешевше за винесення в `shared/` заради одного споживача.
    """
    base = {"api_keys": [KEY], "rate_limit_per_minute": 30, "budget_usd_per_day": 1.0}
    return Settings(**{**base, **kwargs})


class Falls:
    """Клієнт, що відмовляє на кожному виклику. Роль: недоступна залежність."""

    class chat:  # noqa: N801
        class completions:  # noqa: N801
            @staticmethod
            def create(**_kwargs: Any) -> Any:
                raise ConnectionError("провайдер недоступний")


@dataclass(frozen=True)
class Scenario:
    """Один сценарій. Поля після `parts` — те, що має лишитись **після** відповіді.

    :param script: кроки підробленої моделі. Порожньо — текст-заглушка; сценарій, який
        має пройти крізь диспетчер інструментів етапу 1, мусить попросити інструмент, бо
        інакше та гілка етапу 1 не виконується взагалі й лише виглядає зібраною.
    :param breaks: сценарій навмисно ламає частину. Сервіс має лишитись живим, а
        відповідь — назвати, що саме відмовило (ADR-0006).
    """

    name: str
    key: str
    question: str
    branch: str
    parts: tuple[str, ...]
    remembered: bool
    ok: bool = True
    kind: str = "ok"
    tools: tuple[str, ...] = ()
    script: tuple[dict[str, Any], ...] = ()
    breaks: str = ""


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        name="знання з бази",
        key=KEY,
        question="Скільки днів на повернення товару?",
        branch=SEARCH,
        parts=("s06", "s02"),
        remembered=False,
    ),
    Scenario(
        name="замовлення через роутер",
        key=KEY,
        question="Де моє замовлення 4471?",
        branch=ROUTED,
        parts=("s06", "s02", "s03"),
        remembered=False,
    ),
    Scenario(
        name="довільне питання циклом агента",
        key=KEY,
        question="Яка зараз погода в Києві?",
        branch=AGENT,
        parts=("s06", "s02", "s01"),
        remembered=False,
        tools=("get_weather",),
        script=(tool_call("get_weather", {"city": "Київ"}), text("У Києві зараз ясно.")),
    ),
    Scenario(
        name="прохання запам'ятати",
        key=KEY,
        question="Запам'ятай: мій улюблений розмір — M.",
        branch=AGENT,
        parts=("s06", "s02", "s01", "s05"),
        remembered=True,
    ),
    Scenario(
        name="чужий ключ",
        key=STRANGER,
        question="Скільки днів на повернення товару?",
        branch="",
        parts=(),
        remembered=False,
        ok=False,
        kind="unauthenticated",
    ),
    Scenario(
        name="частина відмовляє",
        key=KEY,
        question="Яка зараз погода в Києві?",
        branch="",
        parts=("s06", "s02"),
        remembered=False,
        ok=False,
        kind="dependency_down",
        breaks="s01",
    ),
)


@dataclass
class Outcome:
    """Що сталося насправді. Порівнюється з очікуваним **цілком**, не лише текстом."""

    scenario: Scenario
    ok: bool
    kind: str
    branch: str
    parts: tuple[str, ...]
    remembered: bool
    tools: tuple[str, ...] = ()
    text: str = ""
    mismatch: list[str] = field(default_factory=list)

    def compare(self) -> list[str]:
        """Чим фактичне розійшлося з очікуваним. Порожньо — сценарій пройшов."""
        wrong = []
        if self.ok != self.scenario.ok:
            wrong.append(f"ok: {self.ok} замість {self.scenario.ok}")
        if self.kind != self.scenario.kind:
            wrong.append(f"вид: {self.kind!r} замість {self.scenario.kind!r}")
        if self.branch != self.scenario.branch:
            wrong.append(f"гілка: {self.branch!r} замість {self.scenario.branch!r}")
        if self.parts != self.scenario.parts:
            wrong.append(f"частини: {list(self.parts)} замість {list(self.scenario.parts)}")
        if self.remembered != self.scenario.remembered:
            wrong.append(f"памʼять: {self.remembered} замість {self.scenario.remembered}")
        if self.tools != self.scenario.tools:
            wrong.append(f"інструменти: {list(self.tools)} замість {list(self.scenario.tools)}")
        return wrong


def client_for(scenario: Scenario) -> Any:
    """Клієнт під сценарій: свої кроки, а для «ламає частину» — той, що відмовляє."""
    if scenario.breaks:
        return Falls()
    return FakeLLM(script=list(scenario.script) or [text("51")], repeat_last=True)


def build(tmp: Path, tracer: Any, *, client: Any = None, base: Any = None) -> Capstone:
    """Сервіс для сценаріїв. Усе подається ззовні — як на етапі 6.

    `base` необовʼязковий, але не задарма: без нього `Capstone` індексує базу знань на
    кожному створенні, тобто пʼять разів за прогін сценаріїв.
    """
    return Capstone(
        settings=demo_settings(),
        counters=InMemory(),
        client=client or FakeLLM(script=[text("51")], repeat_last=True),
        tracer=tracer,
        memory_path=tmp / "facts.jsonl",
        base=base,
    )


def play(service: Capstone, scenario: Scenario) -> Outcome:
    """Прогнати один сценарій і зібрати **фінальний стан**, а не лише відповідь."""
    before = len(service.memory.all_facts())
    reply = service.ask(scenario.key, scenario.question, now=NOW)
    after = len(service.memory.all_facts())
    outcome = Outcome(
        scenario=scenario,
        ok=reply.ok,
        kind=reply.kind,
        branch=reply.branch,
        parts=reply.parts,
        remembered=after > before,
        tools=reply.tools,
        text=reply.text,
    )
    outcome.mismatch = outcome.compare()
    return outcome


def play_all(tmp: Path, tracer: Any, *, base: Any = None) -> list[Outcome]:
    """Усі шість по черзі, кожен на своєму сервісі: сценарії не мають ділити лічильники."""
    return [
        play(build(tmp, tracer, client=client_for(scenario), base=base), scenario)
        for scenario in SCENARIOS
    ]
