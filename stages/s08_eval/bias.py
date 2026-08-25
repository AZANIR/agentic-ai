"""Детектори біасу судді. Стоять **над** суддею, а не всередині (ADR-0002).

Суддя, який сам себе перевіряє на упередженість, перевіряє власне уявлення про
упередженість. Тому детектор нічого не знає про те, як суддя влаштований: він подає ті самі
дані по-різному й дивиться, чи змінився вердикт.

**Position bias.** Та сама пара двічі: у порядку AB і в порядку BA. Переворотом рахується
випадок, коли **зміст**-переможець першого порядку не є змістом-переможцем другого. Нічия —
окреме значення, а не відсутність вердикта: перехід «перемогла A» → «нічия» теж переворот,
бо вердикт змінився від подачі.

**Length bias.** Дві відповіді на ту саму задачу: коротка правильна й **та сама**, доповнена
правдивим, але зайвим текстом. Порогу тут немає й бути не може: обидві правильні, друга
відрізняється лише зайвиною, тож **будь-яка** строго додатна перевага довшої — це бал за
довжину.

**Знахідка — не оцінка.** Детектор нічого не каже про агента; він каже про **прилад**.
Змішати їх означало б звинуватити агента в поведінці судді.
"""

from __future__ import annotations

from dataclasses import dataclass

from stages.s08_eval.judge import FIRST, TIE, Compared, Judge, Unavailable

A, B = "A", "B"


@dataclass(frozen=True)
class Pair:
    """Дві відповіді на ту саму задачу — фікстури етапу, не дані користувача."""

    task: str
    expected: str
    first: str
    second: str
    note: str = ""


# Ці тексти написав автор етапу. Вони **не є даними користувача**, тож заборона з AC-07b на
# них не поширюється — інакше демонстрацію довелося б показувати самими лише довжинами.
#
# Пари для позиції **зважені навмисно**: обидві відповіді однаково обґрунтовані й однакові
# за довжиною, тож розрізнити їх може лише порядок подачі. Незважена пара показала б суміш
# двох біасів, і читач не знав би, який саме побачив.
POSITION_PAIRS = [
    Pair(
        task="коли буде доставка",
        expected="замовлення доставка завтра",
        first="Замовлення в дорозі, доставка завтра.",
        second="Доставка завтра — замовлення вже їде.",
        note="однаковий зміст, однакова довжина",
    ),
    Pair(
        task="як повернути товар",
        expected="повернення чотирнадцять днів",
        first="Повернення можливе протягом чотирнадцяти днів.",
        second="Протягом чотирнадцяти днів повернення приймається.",
        note="той самий факт, інший порядок слів",
    ),
    Pair(
        task="чи є розстрочка",
        expected="розстрочка три місяці",
        first="Розстрочка доступна на три місяці.",
        second="На три місяці розстрочка передбачена.",
        note="той самий факт, інша побудова",
    ),
]

# Пари для довжини: `first` — коротка правильна, `second` — **вона ж** плюс правдивий, але
# зайвий текст. Зміст не додано; додано лише символи.
LENGTH_PAIRS = [
    Pair(
        task="коли буде доставка",
        expected="замовлення доставка завтра",
        first="Замовлення в дорозі, доставка завтра.",
        second=(
            "Замовлення в дорозі, доставка завтра. Це стандартний термін для вашого "
            "регіону, і він не змінювався від минулого року."
        ),
        note="додано правдиве й непотрібне",
    ),
    Pair(
        task="як повернути товар",
        expected="повернення чотирнадцять днів",
        first="Повернення можливе протягом чотирнадцяти днів.",
        second=(
            "Повернення можливе протягом чотирнадцяти днів. Строк відліковується від дати "
            "отримання, а не від дати оформлення замовлення."
        ),
        note="додано правдиве й непотрібне",
    ),
]


def _content(order: tuple[str, str], verdict: Compared) -> str:
    """Який **зміст** переміг, незалежно від того, яким він був за рахунком."""
    if verdict.winner == TIE:
        return TIE
    return order[0] if verdict.winner == FIRST else order[1]


@dataclass(frozen=True)
class Swap:
    """Один прогін пари в обидва боки."""

    pair: Pair
    ab: str
    ba: str

    @property
    def flipped(self) -> bool:
        return self.ab != self.ba


@dataclass(frozen=True)
class Finding:
    """Що показав детектор. `unavailable` — третій стан, не нуль знахідок."""

    kind: str
    checked: int
    found: int
    detail: list[str]
    unavailable: str = ""

    @property
    def biased(self) -> bool:
        return self.found > 0

    def line(self) -> str:
        if self.unavailable:
            return f"{self.kind}: НЕ ОЦІНЕНО — {self.unavailable}"
        verdict = "ЗНАЙДЕНО" if self.biased else "згода"
        return f"{self.kind}: {verdict} — {self.found} із {self.checked}"


def position_sweep(judge: Judge, pairs: list[Pair]) -> Finding:
    """Чи змінює порядок подачі вердикт (AC-05, AC-05b)."""
    swaps, detail = [], []
    for pair in pairs:
        try:
            ab = _content(
                (A, B), judge.compare(pair.task, pair.first, pair.second, expected=pair.expected)
            )
            ba = _content(
                (B, A), judge.compare(pair.task, pair.second, pair.first, expected=pair.expected)
            )
        except Unavailable as error:
            return Finding("position bias", len(pairs), 0, [], str(error))
        swap = Swap(pair, ab, ba)
        swaps.append(swap)
        if swap.flipped:
            detail.append(f"{pair.task}: AB -> {ab}, BA -> {ba}")
    return Finding("position bias", len(pairs), sum(s.flipped for s in swaps), detail)


def length_sweep(judge: Judge, pairs: list[Pair]) -> Finding:
    """Чи виграє довша відповідь без виграшу в змісті (AC-06).

    `first` — коротка, `second` — вона ж плюс зайве. Різниця балів іде в деталь **числом**:
    «суддя трохи схильний» — це враження, а не вимір.
    """
    found, detail = 0, []
    for pair in pairs:
        try:
            short = judge.score(pair.task, pair.first, pair.expected)
            padded = judge.score(pair.task, pair.second, pair.expected)
        except Unavailable as error:
            return Finding("length bias", len(pairs), 0, [], str(error))
        gap = padded.score - short.score
        if gap > 0:
            found += 1
            detail.append(
                f"{pair.task}: {short.score} -> {padded.score} (+{gap} за "
                f"{len(pair.second) - len(pair.first)} зайвих символів)"
            )
    return Finding("length bias", len(pairs), found, detail)
