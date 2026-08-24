"""Той самий конвеєр двічі. Різниця — не всередині, а **в типі повернення**.

    batch(...)     -> Spoken       готова відповідь; віддати раніше неможливо
    streaming(...) -> Iterator     фрагменти; перший іде далі, не чекаючи решти

Асиметрія навмисна (ADR-0003). Функція, що повертає готовий результат, не має **способу**
віддати половину; функція, що повертає ітератор, не має способу приховати, що віддає
частинами. Різниця, видима в сигнатурі, не потребує коментаря — і не розходиться з кодом.

**Стрімінг не робить роботу швидшою.** Він раніше починає віддавати. Загальна тривалість
лишається приблизно тією самою, і саме тому міряти треба **час до першого звуку**, а не
загальний час (AC-02b). Без цього твердження урок продавав би прискорення, якого немає.

**Мовчання — не запит.** Порожнє розпізнавання зупиняє конвеєр **до** виклику моделі: інакше
кожен кашель у мікрофон коштує токенів (AC-09).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from stages.s07_voice.clock import Clock
from stages.s07_voice.measure import Stopwatch, Timing
from stages.s07_voice.stt import Heard, Recogniser
from stages.s07_voice.tts import Spoken, Synthesiser

STT = "розпізнавання"
THINK = "відповідь моделі"
SPEAK = "синтез"
SILENT = "мовчання"


@dataclass(frozen=True)
class Audio:
    """Вхідний звук. Для підробки досить тривалості й того, що там сказано."""

    seconds: float
    says: str


@dataclass
class Reply:
    """Результат прогону: що сказано, скільки це коштувало й чи взагалі був запит."""

    said: str
    timing: Timing
    silent: bool = False


def _hear(audio: Audio, watch: Stopwatch, stt: Recogniser, clock: Clock) -> Heard:
    heard = stt.hear(audio, clock=clock)
    watch.step(STT)
    return heard


def _silence(watch: Stopwatch) -> Reply:
    """Порожній вхід. Ані модель, ані синтез не викликаються."""
    watch.step(SILENT)
    return Reply(said="", timing=watch.done(), silent=True)


def batch(
    audio: Audio,
    *,
    clock: Clock,
    stt: Recogniser,
    tts: Synthesiser,
    think: Any,
) -> Reply:
    """Кожен крок чекає на повне завершення попереднього.

    Час до першого звуку тут дорівнює сумі **всіх** кроків: синтез не може почати, доки
    модель не дописала останнє слово.
    """
    watch = Stopwatch(clock)
    heard = _hear(audio, watch, stt, clock)
    if heard.silent:
        return _silence(watch)

    answer = think(heard.text, clock=clock)
    watch.step(THINK)

    spoken = tts.say(answer, clock=clock)
    watch.step(SPEAK)
    watch.first_audio()

    return Reply(said=spoken.text, timing=watch.done())


@dataclass
class Stream:
    """Стрімінговий прогін: фрагменти й розклад, який заповнюється в міру віддачі.

    Обʼєкт, а не атрибут на функції. Перша редакція писала `streaming.last_timing = ...` —
    тобто стан на рівні модуля, який два одночасні потоки затирають один одному. Це рівно
    та вада, якої вчить етап 6, і вона зʼявилась через десять хвилин після того, як я про
    неї написав урок.

    Розклад заповнюється **під час** ітерації, а не після: читач може подивитись на
    `timing.first_audio` одразу після першого фрагмента — саме тоді, коли число й цікаве.
    """

    chunks: Iterator[Spoken]
    timing: Timing
    silent: bool = False


def streaming(
    audio: Audio,
    *,
    clock: Clock,
    stt: Recogniser,
    tts: Synthesiser,
    think_chunks: Any,
) -> Stream:
    """Перший фрагмент іде в синтез, доки модель ще пише решту.

    Повертає `Stream`, а не список: список довелось би зібрати цілком, тобто дочекатись
    останнього фрагмента — і стрімінг перетворився б на батч із зайвими кроками.
    """
    watch = Stopwatch(clock)
    heard = _hear(audio, watch, stt, clock)
    if heard.silent:
        return Stream(chunks=iter(()), timing=_silence(watch).timing, silent=True)

    def produce() -> Iterator[Spoken]:
        for index, chunk in enumerate(think_chunks(heard.text, clock=clock)):
            watch.step(THINK)
            spoken = tts.say(chunk, clock=clock)
            watch.step(SPEAK)
            if index == 0:
                watch.first_audio()
            yield spoken
        watch.done()

    return Stream(chunks=produce(), timing=watch.timing)
