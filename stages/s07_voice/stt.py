"""Розпізнавання: підробка за замовчуванням, модель за прапорцем.

Затримка підробки підібрана **за порядком величини** реальної: розпізнавання секунди звуку
малою моделлю коштує сотні мілісекунд. Абсолютні числа не збігаються з жодною машиною й не
мають — теза етапу про **архітектуру конвеєра**, а не про швидкодію моделей (ADR-0001).

**Порожній результат — окремий стан, а не порожній рядок.** Мовчання не є запитом, і конвеєр
має зупинитись до виклику моделі, а не після (AC-09).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from stages.s07_voice.clock import Clock

# Скільки мілісекунд коштує розпізнавання однієї секунди звуку. Заміряно за порядком
# величини на малій моделі; точність тут не потрібна, потрібна пропорція.
MILLIS_PER_SECOND_OF_AUDIO = 300.0


@dataclass(frozen=True)
class Heard:
    """Що почули. Порожній текст — не помилка, а стан: людина мовчала."""

    text: str
    seconds: float

    @property
    def silent(self) -> bool:
        return not self.text.strip()


class Recogniser(Protocol):
    name: str

    def hear(self, audio: Any, *, clock: Clock) -> Heard: ...


# Скільки лишається доробити, коли людина вже замовкла, за **стрімінгового**
# розпізнавання. Справжнє розпізнавання йде разом із мовленням: до кінця фрази
# більшість роботи вже зроблена, лишається дописати хвіст.
FINALISE_MILLIS = 120.0


@dataclass
class FakeRecogniser:
    """Повертає заздалегідь відомий текст, витративши правдоподібний час.

    Два режими, і різниця між ними — найбільша в усьому конвеєрі:

        батчевий      чекає кінця фрази, потім розпізнає ВСЕ
        стрімінговий  розпізнає РАЗОМ із мовленням, дописує хвіст

    Саме тут стрімінг виграє найбільше, і це не деталь реалізації: людина, що
    говорила дві секунди, чекає ще 600 мс у першому режимі й 120 мс у другому.
    """

    name: str = "fake-stt"
    millis_per_second: float = MILLIS_PER_SECOND_OF_AUDIO
    incremental: bool = False

    def hear(self, audio: Any, *, clock: Clock) -> Heard:
        seconds = getattr(audio, "seconds", 1.0)
        cost = FINALISE_MILLIS if self.incremental else self.millis_per_second * seconds
        clock.sleep(cost)
        return Heard(text=getattr(audio, "says", ""), seconds=seconds)


def get_recogniser(*, real: bool = False) -> Recogniser:
    """Розпізнавання за режимом. Дефолт — підробка: етап проходиться без вагів моделі."""
    if not real:
        return FakeRecogniser()

    from stages.s07_voice.real import RealRecogniser  # noqa: PLC0415 — лише за прапорцем

    return RealRecogniser()
