"""Демонстрація етапу 7: шість сцен підряд.

    python -m stages.s07_voice.run
    python -m stages.s07_voice.run --real    # справжній годинник: те саме, тільки повільно

Працює **без мікрофона, без моделей і без мережі**. Числа беруться з підробленого годинника,
тож той самий прогін дає те саме число на будь-якій машині — і саме тому про них можна
говорити.

Сцени показують свої критерії приймання:

    1. батчевий конвеєр: число «до» й розклад            AC-01, AC-03
    2. стрімінговий: число «після» на тих самих даних     AC-02
    3. звідки береться різниця — дві різні частини        AC-02b
    4. розподіл: чому p95, а не середнє                   AC-04
    5. barge-in: три входи, три рішення                   AC-05, AC-05b, AC-05c
    6. prefetch: скільки купує й скільки марнує            AC-06, AC-06b

**Головна тут — третя.** Перші дві дають два числа; третя пояснює, чому вони різні, і саме
вона відрізняє результат від загальновідомої фрази «стрімінг швидший».
"""

from __future__ import annotations

import sys

from stages.s07_voice.bargein import Sound, should_interrupt
from stages.s07_voice.clock import FakeClock, get_clock
from stages.s07_voice.measure import summarise
from stages.s07_voice.pipeline import SPEAK, STT, THINK, Audio, batch, streaming
from stages.s07_voice.prefetch import prefetched, synchronous
from stages.s07_voice.stt import FakeRecogniser
from stages.s07_voice.tts import FakeSynthesiser

SAID = Audio(seconds=2.0, says="який статус мого замовлення")
ANSWER = "Замовлення в дорозі. Очікуйте доставку завтра до вечора."
CHUNKS = ["Замовлення в дорозі.", " Очікуйте доставку", " завтра до вечора."]
THINK_MILLIS = 750.0

BANNER = (
    "[FakeClock] Затримки підроблені за порядком величини реальних. Числа — про "
    "архітектуру конвеєра, а не про швидкодію моделей."
)


def _think(_: str, *, clock) -> str:
    clock.sleep(THINK_MILLIS)
    return ANSWER


def _think_chunks(_: str, *, clock):
    for chunk in CHUNKS:
        clock.sleep(THINK_MILLIS / len(CHUNKS))
        yield chunk


def _batch(clock=None):
    return batch(
        SAID,
        clock=clock or FakeClock(),
        stt=FakeRecogniser(),
        tts=FakeSynthesiser(),
        think=_think,
    )


def _stream(clock=None):
    stream = streaming(
        SAID,
        clock=clock or FakeClock(),
        stt=FakeRecogniser(incremental=True),
        tts=FakeSynthesiser(),
        think_chunks=_think_chunks,
    )
    return stream, list(stream.chunks)


def scene_batch() -> None:
    print("1. Батчевий конвеєр — число «до»")
    timing = _batch().timing
    for name, millis in timing.as_rows():
        print(f"   {name:<20} {millis:>6.0f} мс")
    print(f"   {'ДО ПЕРШОГО ЗВУКУ':<20} {timing.first_audio:>6.0f} мс")
    print()
    print("   Найдорожчий крок:", timing.slowest().name)
    print("   Сума кроків дорівнює загальному числу — саме тому секундомір один, а не")
    print("   розкиданий по місцях: інакше щось міряють двічі, а щось не міряють зовсім.")
    print()


def scene_stream() -> None:
    print("2. Стрімінговий конвеєр — число «після» на ТИХ САМИХ даних")
    stream, spoken = _stream()
    for chunk in spoken:
        print(f"   фрагмент: {chunk.text!r}")
    print(f"   {'ДО ПЕРШОГО ЗВУКУ':<20} {stream.timing.first_audio:>6.0f} мс")
    print()
    print("   Ітератор, а не список: список довелось би зібрати цілком, тобто дочекатись")
    print("   останнього фрагмента — і стрімінг перетворився б на батч із зайвими кроками.")
    print()


def scene_where_the_gain_comes_from() -> None:
    print("3. Звідки береться різниця — ДВІ різні частини")
    batched = _batch().timing
    stream, _ = _stream()

    overlap = batched.named(STT) - stream.timing.named(STT)
    answer_batch = batched.named(THINK) + batched.named(SPEAK)
    answer_stream = stream.timing.named(THINK) + stream.timing.named(SPEAK)
    ratio = batched.first_audio / stream.timing.first_audio

    fast = stream.timing.first_audio
    print(f"   до першого звуку:   {batched.first_audio:>6.0f} -> {fast:>4.0f} мс  ({ratio:.1f}x)")
    print(f"   перекриття:         {overlap:>6.0f} мс — розпізнавання йшло РАЗОМ із мовленням")
    print(f"   відповідь коштує:   {answer_batch:>6.0f} мс проти {answer_stream:.0f} мс — однаково")
    print()
    print("   Перша частина зменшує загальний час: робота переїхала в час, коли людина ще")
    print("   говорила. Друга — НЕ зменшує: моделі писати стільки ж, синтезу озвучувати")
    print("   стільки ж. Вона лише починає віддавати раніше.")
    print()
    print("   Плутати їх дорого: перша масштабується з довжиною репліки, друга — ні.")
    print()


def scene_distribution() -> None:
    print("4. Розподіл — чому p95, а не середнє")
    # Дев'яносто швидких прогонів і десять повільних: типовий хвіст будь-якого конвеєра
    # з мережею.
    values = [450.0] * 90 + [1700.0] * 10
    seen = summarise(values)

    print(f"   прогонів:  {seen.runs}")
    print(f"   середнє:   {seen.mean:>6.0f} мс")
    print(f"   p95:       {seen.p95:>6.0f} мс   ({seen.tail_ratio:.1f}x до середнього)")
    print(f"   найгірший: {seen.worst:>6.0f} мс")
    print()
    print("   Середнє — число для звіту. p95 — те, що відчуває користувач: кожен двадцятий")
    print("   прогін учетверо повільніший, і середнє цього майже не помічає.")
    print()
    print("   p95 тут — СПРАВЖНІЙ прогін, а не інтерпольоване число: важливо, що хтось його")
    print("   справді відчув.")
    print()


def scene_bargein() -> None:
    print("5. Barge-in — три входи, три рішення")
    for label, sound in (
        ("шум, 100 мс", Sound(level=0.10, millis=100.0)),
        ("клацання, 80 мс", Sound(level=0.90, millis=80.0)),
        ("мовлення, 300 мс", Sound(level=0.90, millis=300.0)),
    ):
        decision = should_interrupt(sound)
        mark = "ПЕРЕРВАТИ" if decision.interrupt else "не переривати"
        print(f"   {label:<18} {mark:<14} {decision.reason}")
    print()
    print("   Умов дві, і жодної окремо не досить. Детектор лише за рівнем перериває від")
    print("   кашлю; лише за тривалістю — від кондиціонера.")
    print()


def scene_prefetch() -> None:
    print("6. Prefetch — скільки купує й скільки марнує")
    calls: list[str] = []

    def tool() -> None:
        calls.append("call")

    slow = synchronous(tool, clock=FakeClock(), needed=True, tool_millis=500.0)
    fast = prefetched(
        tool, clock=FakeClock(), needed=True, tool_millis=500.0, think_millis=THINK_MILLIS
    )
    wasted = prefetched(
        tool, clock=FakeClock(), needed=False, tool_millis=500.0, think_millis=THINK_MILLIS
    )

    print(f"   синхронно:      {slow.millis + THINK_MILLIS:>6.0f} мс (роздум + інструмент)")
    print(f"   з prefetch:     {fast.millis:>6.0f} мс")
    print(f"   куплено:        {slow.millis + THINK_MILLIS - fast.millis:>6.0f} мс")
    print(f"   коли не треба:  {wasted.note}")
    print()
    print("   Prefetch виконує виклик, який може не знадобитись: це запит до чужої системи,")
    print("   місце в черзі, іноді гроші. Стаття, що закінчується словом «швидше», дає")
    print("   оптимізацію без умов її застосування.")
    print()


def main(*, real: bool = False) -> int:
    clock = get_clock(real=real)
    print(BANNER if not real else "[RealClock] Справжній годинник: числа мигтітимуть.")
    print(f"   годинник: {clock.name}")
    print()

    scene_batch()
    scene_stream()
    scene_where_the_gain_comes_from()
    scene_distribution()
    scene_bargein()
    scene_prefetch()

    print("Живий режим (потрібні мікрофон і моделі):")
    print('    pip install -e ".[voice,s06]"')
    print("    uvicorn stages.s07_voice.ws:create_app --factory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(real="--real" in sys.argv))
