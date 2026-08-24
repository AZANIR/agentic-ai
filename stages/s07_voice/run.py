"""Демонстрація етапу 7: сім сцен підряд.

    python -m stages.s07_voice.run
    python -m stages.s07_voice.run --real    # справжній годинник: те саме, тільки повільно

Працює **без мікрофона, без моделей і без мережі**. Числа беруться з підробленого годинника,
тож той самий прогін дає те саме число на будь-якій машині — і саме тому про них можна
говорити.

Сцени показують свої критерії приймання:

    1. батчевий конвеєр: число «до» й розклад            AC-01, AC-03
    2. стрімінговий: число «після» на тих самих даних     AC-02
    3. звідки береться різниця — дві різні частини        AC-02b
    4. розподіл: сто СПРАВЖНІХ прогонів, p95 і хвіст      AC-04
    5. barge-in: три входи, три рішення                   AC-05, AC-05b, AC-05c
    6. prefetch: скільки купує й скільки марнує            AC-06, AC-06b
    7. трейс: той самий розклад, здобутий інакше          AC-11

**Головна тут — третя.** Перші дві дають два числа; третя пояснює, чому вони різні, і саме
вона відрізняє результат від загальновідомої фрази «стрімінг швидший».
"""

from __future__ import annotations

import sys
from pathlib import Path

from shared.trace import group_by_trace, trace_run
from stages.s07_voice.bargein import Sound, should_interrupt
from stages.s07_voice.clock import get_clock
from stages.s07_voice.measure import summarise
from stages.s07_voice.model import CHUNKS, SLOW_EVERY, THINK_MILLIS, in_chunks, whole
from stages.s07_voice.pipeline import SPEAK, STT, THINK, Audio, batch, streaming
from stages.s07_voice.prefetch import prefetched, synchronous
from stages.s07_voice.stt import FakeRecogniser
from stages.s07_voice.tts import FakeSynthesiser

SAID = Audio(seconds=2.0, says="який статус мого замовлення")
TOOL_MILLIS = 500.0

# Скільки прогонів для розподілу. Під справжнім годинником сто прогонів по півтори секунди
# — це дві з половиною хвилини, тож `--real` бере менше й каже про це вголос.
RUNS = 100
REAL_RUNS = 20

BANNER = (
    "[FakeClock] Затримки підроблені за порядком величини реальних. Числа — про "
    "архітектуру конвеєра, а не про швидкодію моделей."
)


def _batch(clock, *, run: int = 0, tracer=None):
    return batch(
        SAID,
        clock=clock,
        stt=FakeRecogniser(),
        tts=FakeSynthesiser(),
        think=whole(run=run),
        tracer=tracer,
    )


def _stream(clock, *, run: int = 0, tracer=None):
    stream = streaming(
        SAID,
        clock=clock,
        stt=FakeRecogniser(incremental=True),
        tts=FakeSynthesiser(),
        think_chunks=in_chunks(run=run),
        tracer=tracer,
    )
    return stream, list(stream.chunks)


def scene_batch(fresh, tracer) -> None:
    print("1. Батчевий конвеєр — число «до»")
    timing = _batch(fresh(), tracer=tracer).timing
    for name, millis in timing.as_rows():
        print(f"   {name:<20} {millis:>6.0f} мс")
    print(f"   {'ДО ПЕРШОГО ЗВУКУ':<20} {timing.first_audio:>6.0f} мс")
    print()
    print("   Найдорожчий крок:", timing.slowest().name)
    print("   Сума кроків дорівнює загальному числу — саме тому секундомір один, а не")
    print("   розкиданий по місцях: інакше щось міряють двічі, а щось не міряють зовсім.")
    print()


def scene_stream(fresh, tracer) -> None:
    print("2. Стрімінговий конвеєр — число «після» на ТИХ САМИХ даних")
    stream, spoken = _stream(fresh(), tracer=tracer)
    for chunk in spoken:
        print(f"   фрагмент: {chunk.text!r}")
    print(f"   {'ДО ПЕРШОГО ЗВУКУ':<20} {stream.timing.first_audio:>6.0f} мс")
    print()
    print("   Ітератор, а не список: список довелось би зібрати цілком, тобто дочекатись")
    print("   останнього фрагмента — і стрімінг перетворився б на батч із зайвими кроками.")
    print()


def scene_where_the_gain_comes_from(fresh) -> None:
    print("3. Звідки береться різниця — ДВІ різні частини")
    batched = _batch(fresh()).timing
    stream, _ = _stream(fresh())

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


def scene_distribution(fresh, runs: int) -> None:
    print("4. Розподіл — чому p95, а не середнє")
    # Сто СПРАВЖНІХ прогонів, а не список, набраний руками. Розкид вносить модель:
    # `latency(run)` — чиста функція номера прогону, тож хвіст справжній, а повторний
    # прогін демо дає ті самі сто чисел.
    values = [_batch(fresh(), run=run).timing.first_audio for run in range(runs)]
    seen = summarise(values)
    slow = sum(1 for value in values if value > seen.mean)

    print(f"   прогонів:  {seen.runs}   з них повільніших за середнє: {slow}")
    print(f"   середнє:   {seen.mean:>6.0f} мс")
    print(f"   p95:       {seen.p95:>6.0f} мс   ({seen.tail_ratio:.1f}x до середнього)")
    print(f"   найгірший: {seen.worst:>6.0f} мс")
    print()
    print("   Середнє — число для звіту. p95 — те, що відчуває користувач: кожен")
    print(f"   {SLOW_EVERY}-й прогін учетверо повільніший, і середнє цього майже не помічає.")
    print()
    print("   p95 тут — СПРАВЖНІЙ прогін, а не інтерпольоване число: важливо, що хтось його")
    print("   справді відчув. І береться найближчим рангом, а не округленням: округлення")
    print("   на половині розмірів вибірки дає ранг на одиницю нижче й ховає хвіст.")
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


def scene_prefetch(fresh, tracer) -> None:
    print("6. Prefetch — скільки купує й скільки марнує")
    calls: list[str] = []

    def tool() -> None:
        calls.append("call")

    both = dict(tool_millis=TOOL_MILLIS, think_millis=THINK_MILLIS)
    slow = synchronous(tool, clock=fresh(), needed=True, **both)
    fast = prefetched(tool, clock=fresh(), needed=True, **both)
    wasted = prefetched(tool, clock=fresh(), needed=False, **both)

    # Обидва числа беруться з тих самих полів того самого типу. Перша редакція додавала
    # час роздуму до синхронного числа ЗЗОВНІ, бо `synchronous` його не спав, — і читач,
    # який порівняв би два `.millis` навпростець, дійшов би протилежного висновку.
    print(f"   синхронно:      {slow.millis:>6.0f} мс (роздум, потім інструмент)")
    print(f"   з prefetch:     {fast.millis:>6.0f} мс (обидва разом)")
    print(f"   куплено:        {slow.millis - fast.millis:>6.0f} мс")
    print(f"   коли не треба:  {wasted.millis:>6.0f} мс відповіді")
    print(f"   змарновано:     {wasted.wasted_millis:>6.0f} мс роботи, яку відкинули")
    print(f"                   {wasted.note}")
    tracer.step("prefetch", bought=slow.millis - fast.millis, wasted=wasted.wasted_millis)
    print()
    print("   Відкинутий виклик НЕ затримує відповідь: на нього просто не чекають. Але він")
    print("   стався — це запит до чужої системи, місце в черзі, іноді гроші. Стаття, що")
    print("   закінчується словом «швидше», дає оптимізацію без умов її застосування.")
    print()


def scene_trace(path: Path | None, trace_id: str) -> None:
    print("7. Трейс — той самий розклад, здобутий іншим механізмом")
    # Саме ЦЯ траєкторія, а не весь файл: `traces/` накопичується між прогонами, і
    # «кроків: 84» після четвертого запуску нічого не сказало б про цей.
    steps = group_by_trace(path).get(trace_id, [])
    kinds = [step["kind"] for step in steps]

    print(f"   траєкторія: {trace_id}   кроків: {len(steps)}")
    print(f"   види кроків: {', '.join(sorted(set(kinds) - {'run_start', 'run_end'}))}")
    for step in steps:
        if step["kind"] == "first_audio":
            print(f"   {step['pipeline']:<10} до першого звуку: {step['millis']:>6.0f} мс")
    print()
    print("   Розклад і трейс — два НЕЗАЛЕЖНІ механізми, і саме тому одним можна звірити")
    print("   інший. Число, що збіглося в обох, помилилось би двічі однаково — а це вже не")
    print("   випадковість. Трейси читатиме етап 8.")
    print()


def main(*, real: bool = False, trace_path: Path | None = None) -> int:
    print(BANNER if not real else "[RealClock] Справжній годинник: числа мигтітимуть.")
    print(f"   годинник: {get_clock(real=real).name}")
    print(f"   фрагментів у відповіді моделі: {len(CHUNKS)}")
    print()

    # Годинник створюється НА КОЖЕН прогін: спільний накопичував би час між сценами, і
    # друга сцена починалася б із того місця, де скінчилась перша. Прапорець доходить
    # сюди, а не лишається в банері — перша редакція друкувала «[RealClock]» і далі
    # будувала `FakeClock()` у кожній сцені.
    def fresh():
        return get_clock(real=real)

    with trace_run("Етап 7 · Voice", path=trace_path, stage="s07") as tracer:
        scene_batch(fresh, tracer)
        scene_stream(fresh, tracer)
        scene_where_the_gain_comes_from(fresh)
        runs = REAL_RUNS if real else RUNS
        if real:
            print(f"   (справжній годинник: {runs} прогонів замість {RUNS} — інакше хвилини)")
        scene_distribution(fresh, runs)
        scene_bargein()
        scene_prefetch(fresh, tracer)
        trace_id = tracer.trace_id
    scene_trace(trace_path, trace_id)

    if trace_path is None:
        print("Трейси прогонів: traces/ — їх читатиме етап 8.")
    print()
    print("Живий режим (потрібні мікрофон і моделі):")
    print('    pip install -e ".[s07,voice]"')
    print("    uvicorn stages.s07_voice.ws:create_real_app --factory")
    print()
    print("Сторінка без моделей — конвеєр і числа працюють, звуку не буде:")
    print('    pip install -e ".[s07]"')
    print("    uvicorn stages.s07_voice.ws:create_app --factory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(real="--real" in sys.argv))
