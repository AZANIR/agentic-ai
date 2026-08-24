"""Переривання голосом: **дві** умови, і жодної окремо не досить.

Найпростіший детектор — один поріг за рівнем: голосніше за поріг, отже, людина говорить. Він
перериває відповідь від кашлю, стуку клавіш і клацання мишею.

Детектор лише за тривалістю перериває від кондиціонера.

    рівень      чи це взагалі голос, а не фон
    тривалість  чи це слово, а не клацання

Обидві — числа, і читач має бачити, **яка саме** спрацювала (ADR-0004).

**Межа названа:** пороги нижче — числа **вправи**, а не налаштування для продакшну.
Справжній залежить від мікрофона, кімнати й мови; спектральний VAD розвʼязує це краще й
тягне окрему залежність та окрему дисципліну.
"""

from __future__ import annotations

from dataclasses import dataclass

# Рівень, вищий за який звук вважається голосом. Умовна шкала 0..1.
SPEECH_LEVEL = 0.35
# Скільки мілісекунд має тривати звук, щоб вважатись словом, а не клацанням.
MIN_SPEECH_MILLIS = 200.0

QUIET = "надто тихо"
SHORT = "надто коротко"
SPEECH = "мовлення"


@dataclass(frozen=True)
class Sound:
    """Шматок вхідного звуку: наскільки гучний і скільки тривав."""

    level: float
    millis: float


@dataclass(frozen=True)
class Decision:
    """Рішення детектора й **причина** — інакше налагодити поріг неможливо."""

    interrupt: bool
    reason: str


def should_interrupt(
    sound: Sound,
    *,
    level: float = SPEECH_LEVEL,
    min_millis: float = MIN_SPEECH_MILLIS,
) -> Decision:
    """Чи переривати відповідь. Причина називається завжди, навіть коли переривати треба.

    Порядок умов тут не має значення для результату — але має для причини: тихий і короткий
    звук назветься тихим, і це правильніше, бо рівень дешевше виміряти й він відсікає більше.
    """
    if sound.level < level:
        return Decision(interrupt=False, reason=f"{QUIET}: {sound.level:.2f} < {level}")
    if sound.millis < min_millis:
        return Decision(
            interrupt=False, reason=f"{SHORT}: {sound.millis:.0f} мс < {min_millis:.0f}"
        )
    return Decision(
        interrupt=True,
        reason=f"{SPEECH}: {sound.level:.2f} ≥ {level} і {sound.millis:.0f} мс ≥ {min_millis:.0f}",
    )
