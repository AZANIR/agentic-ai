"""Секундомір, розклад і розподіл. Числа, а не враження.

**Чому вимірювання окремо від конвеєра.** Розкидані `perf_counter()` по місцях дають числа,
які неможливо скласти: сума кроків не сходиться із загальним, бо щось не поміряли, а щось
поміряли двічі. Один секундомір, який знає про кроки, робить AC-01 («сума дорівнює
загальному») **перевірюваним твердженням**, а не побажанням.

**Чому p95, а не середнє.** Середнє — це число для звіту. p95 — це те, що відчуває
користувач: якщо кожен двадцятий прогін удвічі повільніший, середнє цього майже не помітить,
а людина помітить одразу. Розподіл із довгим хвостом — норма для будь-якого конвеєра з
мережею, і саме хвіст робить голос неприємним.

Одиниця скрізь одна — **мілісекунди**. Змішування секунд і мілісекунд у вимірювальному коді
дає помилку в тисячу разів, яку помічають не одразу, бо число все ще виглядає правдоподібно.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from stages.s07_voice.clock import Clock


@dataclass(frozen=True)
class Step:
    """Один крок конвеєра: імʼя й скільки він коштував."""

    name: str
    millis: float


@dataclass
class Timing:
    """Розклад одного прогону.

    `first_audio` — головне число етапу: час від кінця репліки до першого звуку. `total` —
    уся робота. У батчевому конвеєрі вони збігаються; у стрімінговому — ні, і саме ця
    різниця й є результатом.
    """

    steps: list[Step] = field(default_factory=list)
    # `None`, а не `0.0`. Нуль — хибне значення, тож перевірка «вже позначено?»
    # на ньому не спрацьовувала, і другий виклик мовчки затирав перший. Знайшла
    # це перевірка, яка чекала на помилку й не отримала її.
    first_audio: float | None = None
    total: float = 0.0

    def named(self, name: str) -> float:
        """Скільки коштував крок із цим імʼям. Нуль, якщо кроку не було."""
        return sum(step.millis for step in self.steps if step.name == name)

    def slowest(self) -> Step | None:
        """Найдорожчий крок. Той, який варто оптимізувати першим."""
        return max(self.steps, key=lambda step: step.millis, default=None)

    def as_rows(self) -> list[tuple[str, float]]:
        return [(step.name, step.millis) for step in self.steps]


class Stopwatch:
    """Секундомір, привʼязаний до годинника конвеєра.

    Кроки не перекриваються навмисно: `step()` закриває попередній. Перекриті заміри — це
    ще один спосіб отримати суму, що не сходиться, і найпоширеніший.
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._started = clock.now()
        self._mark = self._started
        self.timing = Timing()

    def step(self, name: str) -> float:
        """Закрити крок під цим імʼям і повернути його вартість."""
        now = self._clock.now()
        cost = now - self._mark
        self._mark = now
        self.timing.steps.append(Step(name=name, millis=cost))
        return cost

    def first_audio(self) -> float:
        """Позначити момент першого звуку. Кличеться **один** раз за прогін."""
        if self.timing.first_audio is not None:
            raise RuntimeError(
                "перший звук позначено двічі. Друге позначення затерло б перше, і число, "
                "заради якого етап існує, стало б часом другого фрагмента"
            )
        self.timing.first_audio = self._clock.now() - self._started
        return self.timing.first_audio

    def done(self) -> Timing:
        """Завершити прогін. Після цього `total` дорівнює сумі кроків."""
        self.timing.total = self._clock.now() - self._started
        return self.timing


@dataclass(frozen=True)
class Distribution:
    """Підсумок багатьох прогонів. Два числа, бо одного замало."""

    runs: int
    mean: float
    p95: float
    worst: float

    @property
    def tail_ratio(self) -> float:
        """У скільки разів p95 гірший за середнє. Саме це число й робить хвіст видимим."""
        return self.p95 / self.mean if self.mean else 0.0


def summarise(values: list[float]) -> Distribution:
    """Розподіл із переліку вимірів.

    p95 береться **найближчим рангом**, без інтерполяції: на ста прогонах це 95-й за
    зростанням. Інтерполяція дала б число, якого не було в жодному прогоні, — а тут важливо,
    що p95 це **справжній** прогін, який хтось справді відчув.
    """
    if not values:
        raise ValueError("розподіл із нуля прогонів не існує")
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, int(round(0.95 * len(ordered))) - 1))
    return Distribution(
        runs=len(ordered),
        mean=sum(ordered) / len(ordered),
        p95=ordered[rank],
        worst=ordered[-1],
    )
