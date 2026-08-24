"""Той самий конвеєр двічі. Різниця — не всередині, а **в типі повернення**.

    batch(...)     -> Reply     готова відповідь; віддати раніше неможливо
    streaming(...) -> Stream    фрагменти; перший іде далі, не чекаючи решти

Асиметрія навмисна (ADR-0003). Функція, що повертає готовий результат, не має **способу**
віддати половину; функція, що повертає ітератор, не має способу приховати, що віддає
частинами. Різниця, видима в сигнатурі, не потребує коментаря — і не розходиться з кодом.

**Стрімінг не робить роботу швидшою.** Він раніше починає віддавати. Виграш складається з
двох різних частин, і плутати їх дорого: перекриття розпізнавання масштабується з довжиною
репліки, раніша віддача — ні (AC-02b).

**Час споживача — не робота конвеєра.** Між фрагментами керування має той, хто їх забирає.
`watch.handover()` закриває цей проміжок окремо, інакше він мовчки додається до наступного
кроку й найдорожчим стає той крок, після якого споживач думав найдовше.

**Мовчання — не запит.** Порожнє розпізнавання зупиняє конвеєр **до** виклику моделі: інакше
кожен кашель у мікрофон коштує токенів (AC-09).

**Кроки пишуться у трейс** — тим самим `shared.trace`, що й на етапах 1–6 (AC-11). Розклад і
трейс — два незалежні механізми, і саме тому одним можна звірити інший. Трасувальник
необовʼязковий: за замовчуванням кроки нікуди не йдуть, тож перевірки не пишуть на диск.
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


class _Untraced:
    """Трасувальник, що нічого не пише. Дефолт, щоб у конвеєрі не було `if tracer:`."""

    def step(self, kind: str, **fields: Any) -> None:
        return None


@dataclass(frozen=True)
class Audio:
    """Вхідний звук.

    Підробці досить тривалості й того, що там сказано; справжньому розпізнаванню потрібні
    `samples`. Два поля замість двох класів: різниця між режимами й так видима в тому,
    який адаптер узяли, і другий тип нічого б не додав.
    """

    seconds: float
    says: str
    samples: bytes = b""


@dataclass
class Reply:
    """Результат прогону: що сказано, скільки це коштувало й чи взагалі був запит."""

    said: str
    timing: Timing
    silent: bool = False


class OnePass:
    """Фрагменти, які можна пройти **один** раз.

    Голий генератор після часткового проходу віддає хвіст: `next(stream.chunks)`, а потім
    `list(stream.chunks)` дає не всю відповідь, а її другу половину — мовчки. Половина
    відповіді, що виглядає як ціла, гірша за помилку.
    """

    def __init__(self, source: Iterator[Spoken]) -> None:
        self._source = source
        self._walked = False

    def __iter__(self) -> Iterator[Spoken]:
        if self._walked:
            raise RuntimeError(
                "фрагменти вже пройдено. Другий прохід віддав би хвіст, а не всю "
                "відповідь — і половина відповіді виглядала б як ціла"
            )
        self._walked = True
        return self._source

    def __next__(self) -> Spoken:
        self._walked = True
        return next(self._source)


@dataclass
class Stream:
    """Стрімінговий прогін: фрагменти й розклад, який заповнюється в міру віддачі.

    Обʼєкт, а не атрибут на функції. Перша редакція писала `streaming.last_timing = ...` —
    тобто стан на рівні модуля, який два одночасні потоки затирають один одному. Це рівно
    та вада, якої вчить етап 6, і вона зʼявилась через десять хвилин після того, як я про
    неї написав урок.

    Розклад заповнюється **під час** ітерації, а не після: читач може подивитись на
    `timing.first_audio` одразу після першого фрагмента — саме тоді, коли число й цікаве.
    `timing.total` при цьому лишається `None`, бо прогін ще триває, і це чесніше за нуль.
    """

    chunks: OnePass
    timing: Timing
    silent: bool = False


def _hear(audio: Audio, watch: Stopwatch, stt: Recogniser, clock: Clock, tracer: Any) -> Heard:
    heard = stt.hear(audio, clock=clock)
    cost = watch.step(STT)
    tracer.step("stt", millis=round(cost, 2), seconds=audio.seconds, silent=heard.silent)
    return heard


def _silence(watch: Stopwatch, tracer: Any) -> Reply:
    """Порожній вхід. Ані модель, ані синтез не викликаються."""
    watch.step(SILENT)
    tracer.step("silence", reason="порожнє розпізнавання — модель не викликано")
    return Reply(said="", timing=watch.done(), silent=True)


def batch(
    audio: Audio,
    *,
    clock: Clock,
    stt: Recogniser,
    tts: Synthesiser,
    think: Any,
    tracer: Any = None,
) -> Reply:
    """Кожен крок чекає на повне завершення попереднього.

    Час до першого звуку тут дорівнює сумі **всіх** кроків: синтез не може почати, доки
    модель не дописала останнє слово.
    """
    tracer = tracer or _Untraced()
    watch = Stopwatch(clock)
    heard = _hear(audio, watch, stt, clock, tracer)
    if heard.silent:
        return _silence(watch, tracer)

    answer = think(heard.text, clock=clock)
    tracer.step("think", millis=round(watch.step(THINK), 2), chunks=1)

    spoken = tts.say(answer, clock=clock)
    tracer.step("speak", millis=round(watch.step(SPEAK), 2), chars=len(spoken.text))
    watch.first_audio()

    timing = watch.done()
    tracer.step("first_audio", millis=round(timing.first_audio or 0.0, 2), pipeline="batch")
    return Reply(said=spoken.text, timing=timing)


def streaming(
    audio: Audio,
    *,
    clock: Clock,
    stt: Recogniser,
    tts: Synthesiser,
    think_chunks: Any,
    tracer: Any = None,
) -> Stream:
    """Перший фрагмент іде в синтез, доки модель ще пише решту.

    Повертає `Stream`, а не список: список довелось би зібрати цілком, тобто дочекатись
    останнього фрагмента — і стрімінг перетворився б на батч із зайвими кроками.
    """
    tracer = tracer or _Untraced()
    watch = Stopwatch(clock)
    heard = _hear(audio, watch, stt, clock, tracer)
    if heard.silent:
        empty: Iterator[Spoken] = iter(())
        return Stream(chunks=OnePass(empty), timing=_silence(watch, tracer).timing, silent=True)

    def produce() -> Iterator[Spoken]:
        for index, chunk in enumerate(think_chunks(heard.text, clock=clock)):
            tracer.step("think", millis=round(watch.step(THINK), 2), chunk=index)
            spoken = tts.say(chunk, clock=clock)
            tracer.step("speak", millis=round(watch.step(SPEAK), 2), chars=len(spoken.text))
            if index == 0:
                watch.first_audio()
                tracer.step(
                    "first_audio",
                    millis=round(watch.timing.first_audio or 0.0, 2),
                    pipeline="streaming",
                )
            yield spoken
            # Керування було в споживача: він слав кадр у сокет, малював рядок, чекав на
            # мережу. Цей час — не робота конвеєра.
            watch.handover()
        timing = watch.done()
        if timing.first_audio is None:
            # Модель не віддала жодного фрагмента. Без цього кроку `first_audio` лишається
            # `None`, сторінка друкує «до першого звуку: 0 мс» — найкраще можливе число
            # для прогону, у якому звуку не було взагалі.
            tracer.step("no_audio", reason="модель не віддала жодного фрагмента")
        tracer.step(
            "total",
            millis=round(timing.total or 0.0, 2),
            handover=round(timing.handover, 2),
        )

    return Stream(chunks=OnePass(produce()), timing=watch.timing)
