"""Синтез: підробка за замовчуванням, модель за прапорцем.

Найважливіше тут — що синтез уміє **починати говорити з фрагмента**. Саме ця властивість і
робить стрімінг можливим: батчевий конвеєр озвучує повну відповідь, стрімінговий — перше
речення, доки решта ще пишеться.

Затримка пропорційна довжині тексту, як і в справжнього синтезу.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from stages.s07_voice.clock import Clock

# Мілісекунд на символ тексту. Знову пропорція, а не абсолютне число.
MILLIS_PER_CHAR = 4.0


@dataclass(frozen=True)
class Spoken:
    """Озвучений шматок. Тривалість — це те, що чує людина, а не те, що коштував синтез.

    `audio` порожній у підробки: етап проходиться без звуку навмисно. Справжній синтез
    кладе туди wav-байти, і саме вони дають сторінці що програти. Байти живуть у памʼяті
    рівно доти, доки їх не відправлено, і на диск не потрапляють (AC-10b).
    """

    text: str
    millis: float
    audio: bytes = b""


class Synthesiser(Protocol):
    name: str

    def say(self, text: str, *, clock: Clock) -> Spoken: ...


@dataclass
class FakeSynthesiser:
    name: str = "fake-tts"
    millis_per_char: float = MILLIS_PER_CHAR

    def say(self, text: str, *, clock: Clock) -> Spoken:
        cost = self.millis_per_char * len(text)
        clock.sleep(cost)
        return Spoken(text=text, millis=cost)


def get_synthesiser(*, real: bool = False) -> Synthesiser:
    if not real:
        return FakeSynthesiser()

    from stages.s07_voice.real import RealSynthesiser  # noqa: PLC0415 — лише за прапорцем

    return RealSynthesiser()
