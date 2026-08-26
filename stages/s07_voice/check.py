"""Перевірки етапу 7.

    python -m stages.s07_voice.check

Працюють **без мікрофона, без моделей і без мережі**. Числа беруться з підробленого
годинника, тож той самий прогін дає те саме число на будь-якій машині (ADR-0002).
"""

from __future__ import annotations

from pathlib import Path

from shared.check_runner import code_mentions, require_intact_source, run_checks
from stages.s07_voice.bargein import (
    MIN_SPEECH_MILLIS,
    QUIET,
    SHORT,
    SPEECH,
    SPEECH_LEVEL,
    Sound,
    should_interrupt,
)
from stages.s07_voice.clock import FakeClock, RealClock, get_clock
from stages.s07_voice.measure import Stopwatch, summarise
from stages.s07_voice.model import ANSWER, CHUNKS, THINK_MILLIS, in_chunks, silent_model, whole
from stages.s07_voice.pipeline import SILENT, SPEAK, STT, THINK, Audio, batch, streaming
from stages.s07_voice.prefetch import WASTED, prefetched, synchronous
from stages.s07_voice.stt import FakeRecogniser
from stages.s07_voice.tts import FakeSynthesiser
from stages.s07_voice.ws import MISSING, missing_models

# Стеля часу для `scripts/check_all.py` — проти розростання, не ціль швидкодії.
BUDGET_SECONDS = 30

NEWLINE = chr(10)

# Одна репліка на весь набір: обидва конвеєри мають міряти те саме.
SAID = Audio(seconds=2.0, says="який статус мого замовлення")

# Скільки коштує інструмент у перевірках prefetch. НАВМИСНО швидший за роздум в одному
# місці й повільніший в іншому: перша редакція скрізь брала 500 проти 600, і випадок
# «інструмент повільніший за роздум» — саме той, у якому відкинутий виклик затримував
# відповідь, — не траплявся ніде.
TOOL_MILLIS = 500.0
SLOW_TOOL_MILLIS = 1_200.0


def _run_batch(clock=None, *, run: int = 0, tracer=None):
    clock = clock or FakeClock()
    return batch(
        SAID,
        clock=clock,
        stt=FakeRecogniser(),
        tts=FakeSynthesiser(),
        think=whole(run=run),
        tracer=tracer,
    )


def _run_stream(clock=None, *, run: int = 0, tracer=None, think_chunks=None):
    clock = clock or FakeClock()
    stream = streaming(
        SAID,
        clock=clock,
        # Стрімінгове розпізнавання — не дрібниця, а найбільший внесок у різницю:
        # воно йде РАЗОМ із мовленням, тож до кінця фрази лишається дописати хвіст.
        stt=FakeRecogniser(incremental=True),
        tts=FakeSynthesiser(),
        think_chunks=think_chunks or in_chunks(run=run),
        tracer=tracer,
    )
    spoken = list(stream.chunks)
    return stream, spoken


# --- два числа --------------------------------------------------------------------------


def check_the_batch_pipeline_reports_first_audio_and_its_parts() -> None:
    """batch: час до першого звуку названо числом, і розклад сходиться"""
    reply = _run_batch()
    timing = reply.timing

    assert reply.said == ANSWER, reply.said
    assert timing.first_audio > 0, timing

    names = [step.name for step in timing.steps]
    assert names == [STT, THINK, SPEAK], names

    # Сума кроків дорівнює загальному числу. Це і є причина, з якої секундомір один, а не
    # розкиданий по місцях: інакше щось міряють двічі, а щось не міряють зовсім.
    assert abs(timing.work() - timing.total) < 0.001, (timing.work(), timing.total)
    assert abs(timing.unaccounted()) < 0.001, timing.unaccounted()
    assert timing.handover == 0.0, "у батчі споживач керування не отримує — віддачі немає"
    assert abs(timing.first_audio - timing.total) < 0.001, (
        "у батчевому конвеєрі перший звук збігається із завершенням: синтез не може почати, "
        "доки модель не дописала останнє слово"
    )


def check_the_streaming_breakdown_adds_up_with_a_slow_consumer() -> None:
    """FAILURE · закон збереження: кроки + віддача = загальний час, і третього доданка немає"""
    clock = FakeClock()
    stream = streaming(
        SAID,
        clock=clock,
        stt=FakeRecogniser(incremental=True),
        tts=FakeSynthesiser(),
        think_chunks=in_chunks(),
    )
    # Споживач НАВМИСНО повільний: рівно так поводиться сокет, який чекає на мережу між
    # фрагментами. Перша редакція приписувала цей час наступному кроку, і «відповідь
    # моделі» показувала 2750 мс при моделі, що спала 750.
    consumer_millis = 1_000.0
    chunks = 0
    for _ in stream.chunks:
        chunks += 1
        clock.sleep(consumer_millis)

    timing = stream.timing
    assert chunks == len(CHUNKS), chunks
    assert abs(timing.unaccounted()) < 0.001, (
        f"{timing.unaccounted():.0f} мс не приписано ані кроку, ані споживачеві: кроки "
        f"{timing.work():.0f} + віддача {timing.handover:.0f} != загальний {timing.total:.0f}. "
        "Розклад, що не сходиться, гірший за відсутній: у нього вірять і оптимізують не те"
    )
    assert abs(timing.handover - consumer_millis * chunks) < 0.001, (
        f"віддача {timing.handover:.0f} мс замість {consumer_millis * chunks:.0f} — час "
        "споживача поміряно неправильно"
    )
    # Дзеркальна половина, і головна: час споживача НЕ приписано моделі. Без неї закон
    # збереження задовольнявся б і тоді, коли модель звинувачують у чужій затримці.
    assert abs(timing.named(THINK) - THINK_MILLIS) < 0.001, (
        f"модель спала {THINK_MILLIS:.0f} мс, а в розкладі коштує {timing.named(THINK):.0f}. "
        "Найдорожчим кроком став той, після якого споживач думав найдовше"
    )


def check_an_unfinished_run_refuses_to_report_a_total() -> None:
    """FAILURE · частково спожитий стрім: `total` — не нуль, а «ще не відомо»"""
    clock = FakeClock()
    stream = streaming(
        SAID,
        clock=clock,
        stt=FakeRecogniser(incremental=True),
        tts=FakeSynthesiser(),
        think_chunks=in_chunks(),
    )
    walk = iter(stream.chunks)
    next(walk)

    timing = stream.timing
    # Число тут НЕ фіксується: перевірка стверджує про `total`, і жорсткий 450 робив
    # би її ще й перевіркою відношення. Дві мутації червонили її замість тієї, яка
    # про них стверджує, — а це розчиняє сигнал, а не підсилює його.
    assert timing.first_audio is not None and timing.first_audio > 0, timing.first_audio
    assert timing.steps, "кроки вже є — прогін іде"
    assert timing.total is None, (
        f"незавершений прогін звітує `total={timing.total}`. Нуль поруч із непорожнім "
        "переліком кроків читається як миттєвий прогін — рівно та сама пастка, що й "
        "`first_audio = 0.0`, лишена в сусідньому полі того самого типу"
    )
    try:
        timing.unaccounted()
    except RuntimeError as error:
        assert "ще не завершено" in str(error), error
    else:
        raise AssertionError("закон збереження порахувався на незавершеному прогоні")


def check_streaming_reaches_first_audio_at_least_twice_as_fast() -> None:
    """stream: час до першого звуку щонайменше вдвічі менший за батчевий"""
    batched = _run_batch().timing
    stream, spoken = _run_stream()

    assert "".join(chunk.text for chunk in spoken) == ANSWER, spoken
    ratio = batched.first_audio / stream.timing.first_audio

    assert ratio >= 2.0, (
        f"батч {batched.first_audio:.0f} мс, стрімінг {stream.timing.first_audio:.0f} мс — "
        f"відношення {ratio:.2f}. Обіцяно щонайменше вдвічі"
    )


def check_the_total_duration_stays_about_the_same() -> None:
    """FAILURE · раніша віддача НЕ зменшує роботи — виграш має дві різні частини"""
    batched = _run_batch().timing
    stream, _ = _run_stream()

    # Порівнюється **відповідь**: модель плюс синтез. Саме тут стрімінг віддає раніше й
    # НЕ робить менше — обсяг роботи той самий, змінився лише момент першої віддачі.
    answer_batch = batched.named(THINK) + batched.named(SPEAK)
    answer_stream = stream.timing.named(THINK) + stream.timing.named(SPEAK)

    assert abs(answer_batch - answer_stream) < 0.001, (
        f"відповідь коштує {answer_batch:.0f} мс у батчі й {answer_stream:.0f} мс у "
        "стрімінгу. Раніша віддача не має зменшувати роботи — інакше число «вдвічі "
        "швидше» порівнює різні обсяги, і урок продає прискорення, якого немає"
    )

    # Друга частина виграшу — інша за природою: розпізнавання **переїхало** в час, коли
    # людина ще говорила. Робота не зникла, вона сталася раніше. Плутати ці дві частини
    # дорого: перша масштабується з довжиною репліки, друга — ні.
    overlap = batched.named(STT) - stream.timing.named(STT)
    assert overlap > 0, (
        f"розпізнавання коштує однаково в обох ({batched.named(STT):.0f} мс) — тоді "
        "перекриття з мовленням не показано, і половина виграшу лишилась непоясненою"
    )
    assert abs((batched.total - stream.timing.total) - overlap) < 0.001, (
        f"різниця загального часу {batched.total - stream.timing.total:.0f} мс не "
        f"дорівнює перекриттю {overlap:.0f} мс — отже, стрімінг десь таки зробив менше "
        "роботи, і це треба назвати, а не сховати"
    )


def check_every_stage_is_named_and_timed() -> None:
    """measure: кожен крок має імʼя й число, і найдорожчий видно"""
    timing = _run_batch().timing

    for step in timing.steps:
        assert step.name and step.millis > 0, step

    slowest = timing.slowest()
    assert slowest is not None, timing.as_rows()
    # Найдорожчий крок має бути ОДИН, а не перший із рівних: інакше `slowest()`
    # повертає те, що трапилось раніше, і читач оптимізує не той крок.
    costs = sorted((step.millis for step in timing.steps), reverse=True)
    assert costs[0] > costs[1], (
        f"два найдорожчі кроки коштують однаково: {timing.as_rows()}. Тоді «який крок оптимізувати "
        f"першим» не має відповіді, а `slowest()` дає ілюзію її"
    )
    assert slowest.millis == costs[0], (slowest, costs)
    assert timing.named(STT) > 0 and timing.named(SPEAK) > 0, timing.as_rows()
    assert timing.named("такого кроку немає") == 0.0


# --- розподіл ---------------------------------------------------------------------------


def check_p95_is_visibly_larger_than_the_mean() -> None:
    """FAILURE · розподіл: p95 помітно більший за середнє — звітують не тим числом"""
    # Дев'яносто швидких прогонів і десять повільних — типовий хвіст будь-якого конвеєра
    # з мережею. Середнє його майже не помічає; людина помічає одразу.
    values = [400.0] * 90 + [1600.0] * 10
    seen = summarise(values)

    assert seen.runs == 100, seen
    assert seen.p95 > seen.mean, seen
    assert seen.tail_ratio >= 1.5, (
        f"p95 {seen.p95:.0f} проти середнього {seen.mean:.0f} — відношення "
        f"{seen.tail_ratio:.2f}. Якщо хвіст не видно, показувати два числа немає сенсу"
    )
    # p95 — це СПРАВЖНІЙ прогін, а не інтерпольоване число, якого ніхто не відчув.
    assert seen.p95 in values, seen.p95


def check_p95_keeps_its_promise_at_every_sample_size() -> None:
    """FAILURE · p95: не більше 5 % прогонів гірші за нього — на БУДЬ-ЯКОМУ розмірі вибірки"""
    # Сто прогонів — щасливе число: там округлення й найближчий ранг збігаються, тож
    # перевірка вище хибу не бачила. Розмірів, на яких вони розходяться, — приблизно
    # половина: 11–19, 30–39, 51–59 …
    for count in (11, 15, 20, 30, 37, 55, 99, 100, 137):
        slow = max(1, count // 10)
        values = [400.0] * (count - slow) + [1600.0] * slow
        seen = summarise(values)
        worse = sum(1 for value in values if value > seen.p95)

        assert worse <= count * 0.05, (
            f"на {count} прогонах p95 = {seen.p95:.0f} мс, але гірших за нього — {worse} "
            f"({worse / count:.1%}). Модуль, що існує рівно щоб показати хвіст, ховає його"
        )
        assert seen.p95 in values, (count, seen.p95)

    # Дзеркальна половина: p95 не має бути й НАДТО високим. Ранг, зсунутий угору, дав би
    # найгірше число під іменем p95 — так само неправда, тільки в інший бік.
    seen = summarise([float(value) for value in range(1, 101)])
    assert seen.p95 == 95.0, f"на 1..100 найближчий ранг дає 95, а не {seen.p95}"


def check_a_distribution_of_nothing_is_refused() -> None:
    """FAILURE · розподіл із нуля прогонів — помилка, а не нулі"""
    try:
        summarise([])
    except ValueError as error:
        assert "нуля" in str(error), error
    else:
        raise AssertionError(
            "порожній перелік дав розподіл. Середнє нуля прогонів — це не нуль, це "
            "відсутність числа, і мовчазний нуль у звіті виглядає як швидкий сервіс"
        )


# --- barge-in ---------------------------------------------------------------------------


def check_noise_does_not_interrupt() -> None:
    """FAILURE · barge-in: тихий звук не перериває відповідь"""
    decision = should_interrupt(Sound(level=0.1, millis=100.0))

    assert not decision.interrupt, decision
    assert QUIET in decision.reason, decision.reason


def check_short_speech_does_not_interrupt() -> None:
    """FAILURE · barge-in: гучний, але короткий звук не перериває — умов дві"""
    decision = should_interrupt(Sound(level=0.9, millis=80.0))

    assert not decision.interrupt, (
        "клацання мишею перервало відповідь. Рівня самого недосить: детектор, що дивиться "
        "лише на гучність, перериває від кашлю й стуку клавіш"
    )
    assert SHORT in decision.reason, decision.reason


def check_speech_does_interrupt_and_says_why() -> None:
    """FAILURE · дзеркальна: мовлення таки перериває — детектор не глухий"""
    decision = should_interrupt(Sound(level=0.9, millis=300.0))

    assert decision.interrupt, (
        "мовлення не перервало відповідь. Детектор, що не перериває ніколи, задовольняє "
        "обидві перевірки вище повністю й при цьому зламаний"
    )
    assert SPEECH in decision.reason and str(int(MIN_SPEECH_MILLIS)) in decision.reason


def check_both_thresholds_actually_decide() -> None:
    """FAILURE · barge-in: кожна з двох умов справді впливає на рішення"""
    loud_long = Sound(level=SPEECH_LEVEL + 0.1, millis=MIN_SPEECH_MILLIS + 10)
    assert should_interrupt(loud_long).interrupt

    # Зсунути будь-який із порогів — і те саме рішення міняється. Без цього твердження
    # обидва числа могли б бути декоративними.
    assert not should_interrupt(loud_long, level=0.99).interrupt, "поріг рівня ні на що не впливає"
    assert not should_interrupt(loud_long, min_millis=10_000).interrupt, (
        "поріг тривалості ні на що не впливає"
    )


# --- prefetch ---------------------------------------------------------------------------


def check_prefetch_buys_a_measured_number_of_milliseconds() -> None:
    """FAILURE · prefetch: два числа порівнюються НАВПРОСТЕЦЬ, без зшивання ззовні"""
    calls: list[str] = []

    def tool() -> None:
        calls.append("called")

    both = {"tool_millis": TOOL_MILLIS, "think_millis": THINK_MILLIS}
    slow = synchronous(tool, clock=FakeClock(), needed=True, **both)
    fast = prefetched(tool, clock=FakeClock(), needed=True, **both)

    assert len(calls) == 2, calls
    # Різниця двох полів `.millis`, і нічого більше. Перша редакція додавала час роздуму
    # до синхронного числа ЗЗОВНІ, бо `synchronous` його не спав: читач, який зробив би
    # очевидне, побачив би, що prefetch на 250 мс ПОВІЛЬНІШИЙ.
    bought = slow.millis - fast.millis
    assert bought > 0, (
        f"prefetch не купив нічого: синхронно {slow.millis:.0f} мс, з prefetch "
        f"{fast.millis:.0f} мс. Тоді складність додано за нуль"
    )
    assert slow.millis == TOOL_MILLIS + THINK_MILLIS, slow
    assert fast.millis == max(TOOL_MILLIS, THINK_MILLIS), fast
    assert bought == min(TOOL_MILLIS, THINK_MILLIS), (
        f"куплено {bought:.0f} мс — а перекриття двох затримок дорівнює меншій із них"
    )


def check_a_discarded_prefetch_does_not_delay_the_answer() -> None:
    """FAILURE · prefetch: на непотрібний результат НЕ чекають — навіть повільний"""
    # Інструмент навмисно ПОВІЛЬНІШИЙ за роздум. Перша редакція спала `max(tool, think)`
    # незалежно від потреби, тож відповідь чекала на результат, який рядком нижче
    # оголошувався марною роботою. Обидві точки виклику були підібрані так (500 проти
    # 600), що різниці не було видно взагалі.
    both = {"tool_millis": SLOW_TOOL_MILLIS, "think_millis": THINK_MILLIS}
    wasted = prefetched(lambda: None, clock=FakeClock(), needed=False, **both)

    assert wasted.millis == THINK_MILLIS, (
        f"відкинутий prefetch затримав відповідь на {wasted.millis:.0f} мс замість "
        f"{THINK_MILLIS:.0f}. Чекати на результат, який відкидаєш, — це не оптимізація"
    )
    assert wasted.wasted_millis == SLOW_TOOL_MILLIS, wasted
    # Дзеркальна половина: коли результат потрібен, на нього таки чекають повністю.
    needed = prefetched(lambda: None, clock=FakeClock(), needed=True, **both)
    assert needed.millis == SLOW_TOOL_MILLIS, (
        f"потрібний результат отримано за {needed.millis:.0f} мс, а інструмент коштує "
        f"{SLOW_TOOL_MILLIS:.0f}. Тоді prefetch віддає відповідь до того, як має її"
    )
    assert needed.wasted_millis == 0.0, needed


def check_an_unused_prefetch_is_named_as_wasted_work() -> None:
    """FAILURE · prefetch: непотрібний виклик відбувся, і це названо марною роботою"""
    calls: list[str] = []
    both = {"tool_millis": TOOL_MILLIS, "think_millis": THINK_MILLIS}
    outcome = prefetched(lambda: calls.append("called"), clock=FakeClock(), needed=False, **both)

    assert calls == ["called"], "prefetch не покликав інструмент — тоді він нічого не купує"
    assert not outcome.used, outcome
    assert WASTED in outcome.note, (
        f"марну роботу не названо: {outcome.note!r}. Prefetch виконує виклик, який може не "
        "знадобитись — етап, що показує лише виграш, агітує, а не вчить"
    )
    # Ціна названа ЧИСЛОМ, а не лише словами. Примітка без числа не дає порівняти виграш
    # із витратою, а етап продає саме порівняння.
    assert outcome.wasted_millis == TOOL_MILLIS, outcome

    # Дзеркальна половина: коли інструмент таки потрібен, марної роботи немає.
    used = prefetched(lambda: None, clock=FakeClock(), needed=True, **both)
    assert used.used and not used.note and used.wasted_millis == 0.0, used


# --- мовчання ---------------------------------------------------------------------------


def check_empty_transcription_calls_neither_model_nor_synthesis() -> None:
    """FAILURE · мовчання — не запит: ані модель, ані синтез не викликаються"""
    clock = FakeClock()
    reply = batch(
        Audio(seconds=1.0, says="   "),
        clock=clock,
        stt=FakeRecogniser(),
        tts=FakeSynthesiser(),
        think=whole(),
    )

    assert reply.silent and reply.said == "", reply
    assert [step.name for step in reply.timing.steps] == [STT, SILENT], reply.timing.as_rows()
    # Доказ не в іменах кроків, а в **затратах**: підроблена модель спить 600 мс, синтез —
    # пропорційно довжині. Якби їх покликали, годинник це показав би.
    assert clock.waits == [FakeRecogniser().millis_per_second * 1.0], clock.waits


def check_streaming_also_refuses_silence() -> None:
    """FAILURE · мовчання зупиняє й стрімінговий конвеєр — обидва, не один"""
    clock = FakeClock()
    stream = streaming(
        Audio(seconds=1.0, says=""),
        clock=clock,
        stt=FakeRecogniser(),
        tts=FakeSynthesiser(),
        think_chunks=in_chunks(),
    )

    assert stream.silent and list(stream.chunks) == [], stream
    assert len(clock.waits) == 1, clock.waits


def check_a_model_that_says_nothing_is_not_reported_as_instant() -> None:
    """FAILURE · порожня відповідь моделі: перший звук — «не було», а не нуль мілісекунд"""
    stream, spoken = _run_stream(think_chunks=silent_model())

    assert spoken == [], spoken
    assert not stream.silent, "мовчала МОДЕЛЬ, а не людина — це різні режими відмови"
    assert stream.timing.first_audio is None, (
        f"порожня відповідь дала `first_audio={stream.timing.first_audio}`. Нуль тут — "
        "найкраща можлива затримка для прогону, у якому звуку не було взагалі, і саме "
        "її сторінка й показувала"
    )
    assert stream.timing.total is not None, "прогін завершився — загальний час має бути"


def check_the_chunks_refuse_a_second_walk() -> None:
    """FAILURE · фрагменти: другий прохід — відмова, а не мовчазний хвіст"""
    stream = streaming(
        SAID,
        clock=FakeClock(),
        stt=FakeRecogniser(incremental=True),
        tts=FakeSynthesiser(),
        think_chunks=in_chunks(),
    )
    first = next(stream.chunks)
    assert first.text == CHUNKS[0], first

    try:
        rest = list(stream.chunks)
    except RuntimeError as error:
        assert "вже пройдено" in str(error), error
    else:
        raise AssertionError(
            f"другий прохід віддав {len(rest)} фрагментів замість відмови — це хвіст "
            "відповіді, а не вся відповідь. Половина відповіді, що виглядає як ціла, "
            "гірша за помилку"
        )


# --- годинник ---------------------------------------------------------------------------


def check_the_pipeline_never_reads_the_system_clock() -> None:
    """FAILURE · годинник: конвеєр не ІМПОРТУЄ жодного джерела недетермінізму"""
    import ast

    here = Path(__file__).parent
    banned = {"time", "datetime", "random", "secrets"}
    for name in ("pipeline.py", "measure.py", "bargein.py", "prefetch.py", "stt.py", "tts.py"):
        source = (here / name).read_text(encoding="utf-8")

        # Розбір ІМПОРТІВ, а не пошук слів. Перша редакція грепала три імені —
        # `perf_counter`, `monotonic`, `time.time`, — і крізь неї спокійно проходили
        # `datetime.now()`, `time.time_ns()` та `random`. Перелік слів завжди неповний;
        # перелік модулів, з яких недетермінізм узагалі може прийти, — ні.
        tree = ast.parse(source)
        imported = {
            (alias.name if isinstance(node, ast.Import) else node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (node.names if isinstance(node, ast.Import) else [None])
        }
        assert not (imported & banned), (
            f"{name} імпортує {sorted(imported & banned)}. Тоді перевірка часу залежить від "
            "навантаження машини, падає раз на десять прогонів — і її вимикають разом із "
            "єдиним доказом головної тези етапу"
        )
        # Дзеркальна половина: навіть без імпорту модуля годинник міг би прийти через
        # передане ззовні імʼя. Слова лишаються другою лінією, не першою. `now` сюди НЕ
        # входить: `clock.now()` — це і є законний спосіб спитати час.
        found = code_mentions(source, {"perf_counter", "monotonic", "time_ns", "utcnow"})
        assert not found, f"{name} читає системний годинник: {found}"


def check_two_runs_in_flight_do_not_corrupt_each_other() -> None:
    """FAILURE · два стріми одночасно: розклади не змішуються (NFR-6)"""
    # Двадцять послідовних прогонів давали однакове число ЗА ПОБУДОВОЮ: кожен будував
    # власний `FakeClock` над чистою функцією. Мигтіння, від якого існує NFR-6, вони
    # спостерігати не могли. Небезпечна форма — стан на рівні модуля, і видно її лише
    # тоді, коли два прогони живуть ОДНОЧАСНО.
    first, second = (
        streaming(
            SAID,
            clock=FakeClock(),
            stt=FakeRecogniser(incremental=True),
            tts=FakeSynthesiser(),
            think_chunks=in_chunks(),
        )
        for _ in range(2)
    )
    walk_a, walk_b = iter(first.chunks), iter(second.chunks)
    for _ in range(len(CHUNKS)):
        next(walk_a)
        next(walk_b)

    assert first.timing is not second.timing, (
        "два прогони поділяють один розклад — тобто стан живе на рівні модуля, і друга "
        "розмова затирає числа першої. Саме ця вада вже була тут одного разу"
    )
    for timing in (first.timing, second.timing):
        assert [step.name for step in timing.steps] == [STT, *[THINK, SPEAK] * len(CHUNKS)]
    # Рівність МІЖ прогонами, а не з літералом: перевірка про втручання одного прогону
    # в інший не має червоніти від того, що змінилось саме число.
    assert first.timing.first_audio == second.timing.first_audio is not None, (
        f"{first.timing.first_audio} проти {second.timing.first_audio}"
    )

    # І дзеркально: двадцять послідовних прогонів теж дають одне число. Слабше твердження,
    # але саме воно записане в NFR-6, тож лишається — з чесним іменем.
    assert len({_run_batch().timing.first_audio for _ in range(20)}) == 1


def check_the_fake_clock_does_not_actually_sleep() -> None:
    """FAILURE · підроблений годинник не спить — інакше двадцять прогонів коштували б хвилини"""
    import time as real_time

    started = real_time.perf_counter()
    clock = FakeClock()
    clock.sleep(5_000.0)
    elapsed = (real_time.perf_counter() - started) * 1000.0

    assert clock.now() == 5_000.0, clock.now()
    assert elapsed < 50.0, (
        f"підроблений годинник спав {elapsed:.0f} мс насправді. Тоді прогін «на півтори "
        "секунди» коштує півтори секунди, а двадцять прогонів — пів хвилини"
    )


def check_the_clock_factory_defaults_to_fake() -> None:
    """FAILURE · фабрика: дефолт — підробка; справжній годинник лише за прапорцем"""
    assert isinstance(get_clock(), FakeClock), type(get_clock())
    assert isinstance(get_clock(real=True), RealClock), type(get_clock(real=True))

    # І дзеркально: справжній годинник справді рухається сам.
    real = RealClock()
    assert real.now() > 0


def check_the_stopwatch_refuses_a_second_first_audio() -> None:
    """FAILURE · секундомір: перший звук позначається один раз"""
    watch = Stopwatch(FakeClock())
    watch.first_audio()
    try:
        watch.first_audio()
    except RuntimeError as error:
        assert "двічі" in str(error), error
    else:
        raise AssertionError(
            "перший звук позначено двічі мовчки. Друге позначення затерло б перше, і число, "
            "заради якого етап існує, стало б часом другого фрагмента"
        )


# --- сторінка й живий режим ----------------------------------------------------------------

HERE = Path(__file__).parent
PAGE = HERE / "page.html"


def _script() -> str:
    """Тіло `<script>` сторінки. Стиль і розмітку перевіряти немає за чим."""
    page = PAGE.read_text(encoding="utf-8")
    return page[page.index("<script>") : page.index("</script>")]


def check_the_microphone_needs_an_explicit_action() -> None:
    """FAILURE · сторінка: мікрофон береться лише в тілі `start()`, і зупинка звільняє"""
    script = _script()

    # Позиційне включення, а не сусідство рядків. Перша редакція різала текст по ПЕРШОМУ
    # `getUserMedia` і питала, чи є `addEventListener` праворуч, — а він там є завжди,
    # бо внизу файлу стоїть `pagehide`. Права половина `or` була істинна для будь-якої
    # сторінки з одним слухачем подій, і винесення `getUserMedia` на рівень модуля —
    # тобто рівно порушення AC-10 — лишало перевірку зеленою.
    uses = [i for i in range(len(script)) if script.startswith("getUserMedia", i)]
    assert len(uses) == 1, f"getUserMedia згадано {len(uses)} разів — має бути рівно одне місце"

    opens = script.index("async function start")
    closes = script.index("function onMessage")
    assert opens < uses[0] < closes, (
        "getUserMedia викликається поза тілом `start()` — мікрофон береться при "
        "завантаженні сторінки. Це порушення згоди незалежно від того, що робиться зі "
        "звуком далі, і браузер має рацію, коли питає"
    )

    # Дзеркальна половина: пристрій звільняється. Червона крапка, що лишається горіти після
    # переходу на іншу сторінку, — це не косметика, це недотримана обіцянка.
    assert "getTracks().forEach" in script and "track.stop()" in script, (
        "доріжки не зупиняються — мікрофон лишається зайнятим після зупинки"
    )
    assert "pagehide" in script, "закриття вкладки не звільняє пристрій"


def check_the_page_recovers_from_a_failure_after_permission() -> None:
    """FAILURE · сторінка: помилка ПІСЛЯ дозволу звільняє мікрофон і не вбиває кнопку"""
    script = _script()

    # Найгірший стан сторінки: дозвіл узято, мікрофон живий, крапка горить — і зламалось
    # щось далі. Перша редакція ловила лише сам `getUserMedia`; `new WebSocket` (помилка
    # безпеки при відкритті по https) і `new MediaRecorder` (немає кодека) летіли з
    # `start()` назовні, `talk.disabled = false` не виконувався ніколи, і звільнити
    # пристрій було нічим.
    body = script[script.index("async function start") : script.index("function onMessage")]
    after_permission = body[body.index("getUserMedia") :]
    for risky in ("new WebSocket", "new MediaRecorder"):
        assert risky in after_permission, f"{risky} не в тілі start() — перевірка дивиться не туди"
    assert after_permission.count("try {") >= 1 and "stop();" in after_permission, (
        "виклики після дозволу не обгорнуті, або обробник не звільняє пристрій: "
        "мікрофон лишиться увімкненим, а звільнити його буде нічим"
    )

    handler = script[script.index('talk.addEventListener("click"') :]
    assert "} finally {" in handler and "talk.disabled = false" in handler, (
        "кнопка вмикається назад останнім рядком тіла, а не у `finally`. Будь-яка помилка "
        "всередині лишає її навіки вимкненою — при живому мікрофоні"
    )


def check_the_page_shows_what_actually_happened_not_what_it_intended() -> None:
    """FAILURE · сторінка: обірваний сокет гасить індикатор, а порожня відповідь — не нуль"""
    script = _script()

    # Сервер закриває сокет у гілці «моделей немає» і при будь-якій помилці адаптера.
    # Без цих двох обробників сторінка цього не помічала: індикатор далі показував
    # «слухаю» з червоною крапкою, а рекордер стріляв кожні 200 мс у мертвий сокет.
    for handler in ("socket.onclose", "socket.onerror"):
        assert handler in script, f"{handler} немає — індикатор показує намір, а не стан"
    assert 'kind === "chunk"' in script, (
        "сторінка не має гілки для фрагментів, хоч сокет шле саме їх — відповіді не видно"
    )
    # `null` — не нуль. Порожня відповідь моделі лишає перший звук непозначеним, і
    # показати «0 мс» означало б віддати найкращу можливу затримку за прогін без звуку.
    assert "=== null" in script and '"—"' in script, (
        "сторінка не відрізняє «звуку не було» від «звук миттєвий»"
    )


def check_the_page_writes_down_numbers_and_nothing_else() -> None:
    """FAILURE · сеанс лишає числа — і не лишає ані семплів, ані тексту"""
    page = PAGE.read_text(encoding="utf-8")
    socket = (HERE / "ws.py").read_text(encoding="utf-8")

    # Перелік — про ЗБЕРІГАННЯ, і кожен запис у ньому має зуби. Перша редакція мала тут
    # `wav` із приписом `or forbidden == "wav"`: сторож, знерухомлений під власний код
    # (`data:audio/wav;base64` у гілці програвання). `data:`-URI — це не сховище, тож
    # слово пішло геть, а `write_text`, якого бракувало, стало на його місце: мутація
    # «ws.py пише розпізнане у файл через write_text» проходила крізь перевірку наскрізь.
    forbidden = ("localStorage", "indexedDB", "sessionStorage", "write_bytes", "write_text")
    for name, source in (("page.html", page), ("ws.py", socket)):
        for word in forbidden:
            assert word not in source, f"{name} зберігає щось із сеансу: {word!r}"
    assert "open(" not in socket.replace("wave.open(", "").replace(".open(", ""), (
        "ws.py відкриває файл — сеанс має лишати числа й нічого більше"
    )

    # Дзеркальна половина: числа таки лишаються. Сеанс, що не лишає нічого, задовольняє
    # «звук не зберігається» повністю й робить етап невимірюваним.
    assert "first_audio" in socket and "as_rows" in socket, (
        "сокет не віддає розкладу — тоді сторінка не може показати ті самі кроки, що прогін"
    )


def check_a_missing_model_is_explained_not_crashed() -> None:
    """FAILURE · відсутня модель: сказано, що встановити, а не технічна помилка"""
    # ОБИДВІ гілки, а не та, якій пощастило на цій машині. Перша редакція писала
    # `assert absent is None or absent == MISSING` — істинне завжди, — і шлях «моделі на
    # місці» не виконувався ніде. А він і був зламаний: `stages.s07_voice.real` не існував.
    assert missing_models(("json", "pathlib")) is None, "наявні модулі оголошено відсутніми"
    assert missing_models(("no_such_module_xyz",)) == MISSING, "відсутній модуль не помічено"

    # Справжній перелік має включати ВЛАСНИЙ модуль етапу, а не лише чужі пакети: саме
    # його відсутність давала голий трейсбек тим, хто виконав інструкцію й усе встановив.
    from stages.s07_voice.ws import VOICE_MODULES

    assert "stages.s07_voice.real" in VOICE_MODULES, VOICE_MODULES
    assert missing_models() is None or missing_models() == MISSING

    # Повідомлення має містити КОМАНДУ. Читач, який бачить `ModuleNotFoundError`,
    # дізнається менше, ніж читач, який бачить, що набрати.
    assert "pip install" in MISSING, MISSING
    assert "ModuleNotFoundError" not in MISSING, MISSING
    # І має сказати, що працює без моделей: інакше читач вирішить, що етап зламався.
    assert "run" in MISSING, MISSING


def check_the_live_mode_actually_exists_and_is_reachable() -> None:
    """FAILURE · живий режим: адаптери існують, і задокументована команда веде саме до них"""
    import ast

    # Перша редакція лишила `from stages.s07_voice.real import …` у двох фабриках, а файлу
    # не написала. Читач, який виконав інструкцію й ВСТАНОВИВ пакети, отримував
    # `ModuleNotFoundError`; читач, який їх не встановив, отримував ввічливе повідомлення.
    # Інструкція карала за те, що їй підкорилися.
    real = HERE / "real.py"
    assert real.exists(), "stages/s07_voice/real.py немає — живий режим не існує"
    names = {
        node.name
        for node in ast.walk(ast.parse(real.read_text(encoding="utf-8")))
        if isinstance(node, ast.ClassDef)
    }
    assert {"RealRecogniser", "RealSynthesiser"} <= names, names

    # `--factory` не вміє передавати аргументів, тож `create_app` завжди піднімався з
    # `real=False`: підроблені адаптери поруч із проханням встановити гігабайти моделей.
    socket = (HERE / "ws.py").read_text(encoding="utf-8")
    demo = (HERE / "run.py").read_text(encoding="utf-8")
    assert "def create_real_app()" in socket, "живий режим не має власної фабрики"
    assert "ws:create_real_app --factory" in demo, (
        "демо друкує команду, що піднімає підробку, і поруч просить встановити моделі"
    )

    # І остання ланка: пакети, які демо каже встановити, мають існувати й давати те, що
    # потрібно наступному рядку. Перша редакція просила `.[voice]` — там лише ваги
    # моделей, — а далі наказувала запустити `uvicorn`, якого той extra не приносить.
    extras = (Path(__file__).parents[2] / "pyproject.toml").read_text(encoding="utf-8")
    for name in ("s07", "voice"):
        assert f"{name} = [" in extras, f"демо просить `.[{name}]`, а такого extra немає"
    web = extras[extras.index("s07 = [") : extras.index("]", extras.index("s07 = ["))]
    for package in ("fastapi", "uvicorn"):
        assert package in web, (
            f"`.[s07]` не приносить {package}, а наступний рядок інструкції його кличе. "
            "Інструкція, що карає за послух, гірша за її відсутність"
        )


def check_the_socket_reuses_the_pipeline_it_does_not_copy_it() -> None:
    """FAILURE · сокет бере ТОЙ САМИЙ конвеєр — інакше числа розійдуться (AC-11)"""
    socket = (HERE / "ws.py").read_text(encoding="utf-8")

    assert "from stages.s07_voice.pipeline import" in socket, (
        "сокет не імпортує конвеєра. Власна копія кроків означає, що числа на сторінці й "
        "числа у прогоні можуть розійтися, і жодне не перевіряється другим"
    )
    # І не має власних затримок: усе, що спить, живе в адаптерах. Перша редакція писала
    # `not code_mentions(...) or "clock.sleep" in socket` — а `clock.sleep` був у ws.py
    # завжди, тож права половина рятувала будь-що: додавання `time.sleep(0.5)` перевірку
    # не червонило.
    assert not code_mentions(socket, {"sleep"}), (
        f"сокет має власні затримки: {code_mentions(socket, {'sleep'})}. Усе, що спить, "
        "живе в адаптерах — інакше числа сокета й числа прогону міряють різне"
    )
    # І окремо: синхронний конвеєр не виконується просто в корутині. `RealClock.sleep`
    # там тримає event loop, і 750 мс роздуму одного клієнта — це 750 мс тиші для всіх
    # інших на тому ж воркері. Урок етапу 6 про це саме.
    assert "to_thread.run_sync" in socket, (
        "крок конвеєра виконується в корутині — дві одночасні розмови серіалізуються"
    )


def check_the_trace_carries_the_same_breakdown_as_the_timing() -> None:
    """FAILURE · трейс і розклад — два механізми, і одним звіряється інший (AC-11)"""
    import tempfile
    from pathlib import Path as _Path

    from shared.trace import group_by_trace, trace_run

    with tempfile.TemporaryDirectory() as tmp:
        path = _Path(tmp) / "t.jsonl"
        with trace_run("s07", path=path, stage="s07") as tracer:
            batched = _run_batch(tracer=tracer).timing
            stream, _ = _run_stream(tracer=tracer)
            trace_id = tracer.trace_id
        steps = group_by_trace(path)[trace_id]

    marks = {s["pipeline"]: s["millis"] for s in steps if s["kind"] == "first_audio"}
    assert marks == {"batch": batched.first_audio, "streaming": stream.timing.first_audio}, (
        f"трейс каже {marks}, розклад — батч {batched.first_audio:.0f}, стрім "
        f"{stream.timing.first_audio:.0f}. Два механізми розійшлися, і жодному не можна вірити"
    )

    # Кроки моделі у трейсі мають скластися в те саме число, що й крок розкладу. Це і є
    # звірка: одне джерело помилилось би, два однаково — навряд.
    traced_think = sum(s["millis"] for s in steps if s["kind"] == "think" and "chunk" in s)
    assert abs(traced_think - stream.timing.named(THINK)) < 0.01, (
        f"трейс: {traced_think:.0f} мс моделі, розклад: {stream.timing.named(THINK):.0f}"
    )
    # І дзеркально: трейс НЕ несе тексту відповіді. Розмова лишає числа, не зміст.
    assert not any(ANSWER[:12] in str(step) for step in steps), (
        "трейс несе текст відповіді — сеанс має лишати числа й нічого більше (AC-10b)"
    )


def check_the_socket_actually_runs_a_conversation() -> None:
    """FAILURE · живий режим ЗАПУСКАЄТЬСЯ — читання файлу цього не доводить"""
    import json

    from shared.check_runner import NotVerified

    try:
        from fastapi.testclient import TestClient  # noqa: PLC0415
    except ImportError as error:
        # Веб-фреймворка на базовій установці немає, і це не червоне: різниця між
        # «збіглося» і «не перевіряли» має лишатись видимою.
        raise NotVerified(f"fastapi не встановлено: {error}") from error

    from stages.s07_voice.ws import create_app  # noqa: PLC0415

    # Ця перевірка існує через найдорожчу знахідку етапу. Сокет не працював НІКОЛИ —
    # ані з моделями, ані без: `from __future__ import annotations` робив анотацію
    # рядком, `WebSocket` імпортувався всередині фабрики, і FastAPI вважав `socket`
    # query-параметром, закриваючи кожне зʼєднання з кодом 1008 ще до `accept()`.
    # Два рев'ю прочитали цей файл і не побачили нічого. Знайшов перший запуск.
    client = TestClient(create_app())
    assert client.get("/").status_code == 200, "сторінка не віддається"

    with client.websocket_connect("/voice") as socket:
        socket.send_text(json.dumps({"seconds": 0.2}))
        for _ in range(10):  # дві секунди мовлення
            socket.send_bytes(b"x" * 800)
        # Конвеєр має чекати на КІНЕЦЬ репліки: час до першого звуку рахується від неї.
        socket.send_text(json.dumps({"end": True}))

        chunks = []
        while True:
            message = socket.receive_json()
            if message["kind"] != "chunk":
                break
            chunks.append(message["text"])

    timing = message["timing"]
    assert "".join(chunks) == ANSWER, chunks
    assert timing["first_audio"] is not None and timing["first_audio"] > 0, timing
    work = sum(millis for _, millis in timing["steps"])
    assert abs(work + timing["handover"] - timing["total"]) < 0.001, (
        f"розклад сокета не сходиться: {work} + {timing['handover']} != {timing['total']}"
    )
    # Дзеркальна половина: кадри НЕ запускають конвеєр по одному. Тривалість репліки має
    # дорівнювати сумі кадрів, а не тривалості останнього.
    recognised = dict(timing["steps"])[STT]
    assert recognised > 1_000 * 0.2, (
        f"розпізнавання коштувало {recognised:.0f} мс — стільки коштує ОДИН кадр. Конвеєр "
        "запускається на кожні 200 мс замість того, щоб дочекатись кінця репліки"
    )


def check_the_web_module_is_not_imported_on_a_bare_install() -> None:
    """FAILURE · перевірки не тягнуть веб-фреймворк — інакше базова установка червоніє"""
    import ast

    # Розбір ІМПОРТІВ, а не пошук у тексті. Перша редакція шукала рядок
    # «...import create_app» — і знаходила його у власному ж повідомленні про помилку.
    # Пʼятий випадок цієї пастки в курсі: перевірка про код має дивитись на код.
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))

    def names_from(nodes) -> set[str]:
        return {
            alias.name
            for node in nodes
            if isinstance(node, ast.ImportFrom) and node.module == "stages.s07_voice.ws"
            for alias in node.names
        }

    # На РІВНІ МОДУЛЯ, а не будь-де. Імпорт усередині функції виконується лише тоді, коли
    # ту функцію покликали, — саме так перевірка живого режиму й бере `create_app`, не
    # ламаючи базову установку. Заборона «ніде» вбила б і цей законний шлях.
    top_level = names_from(tree.body)
    assert "create_app" not in top_level, (
        f"перевірки імпортують {sorted(top_level)} на рівні модуля — `create_app` тягне "
        "веб-фреймворк, і на базовій установці це червоне замість «не перевірено»"
    )
    # Дзеркальна половина: щось із `ws` імпортувати таки треба, інакше перевірка
    # відсутньої моделі нічого не перевіряє.
    assert "missing_models" in top_level, top_level
    # І друга: `create_app` таки має братися — усередині функції. Без цього набір не
    # виконує сокета жодного разу, а саме читання файлу вже одного разу пропустило те,
    # що живий режим не працює взагалі.
    assert "create_app" in names_from(ast.walk(tree)), (
        "жодна перевірка не бере `create_app` — сокет ніхто не запускає, а прочитаний "
        "файл не доводить, що він піднімається"
    )


# --- e2e: демо ------------------------------------------------------------------------------


SCENES = 7


def check_the_demo_shows_every_scene_with_real_numbers() -> None:
    """e2e · демо показує сім сцен, обидва числа й обидві частини виграшу"""
    import io
    import tempfile
    from contextlib import redirect_stdout
    from pathlib import Path as _Path

    from stages.s07_voice.run import main as demo_main

    buffer = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp:
        # Трейс — у тимчасовий файл. Інакше перевірки лишають по собі записи у `traces/`,
        # а сцена 7 читає їх разом із чужими.
        with redirect_stdout(buffer):
            code = demo_main(trace_path=_Path(tmp) / "t.jsonl")
    output = buffer.getvalue()

    assert code == 0, code
    assert output.startswith("[FakeClock]"), output.splitlines()[0]
    for number in range(1, SCENES + 1):
        assert f"{NEWLINE}{number}. " in output, f"сцена {number} не надрукувалась"

    # Тіла сцен, а не заголовки. Числа мають бути ті самі, що дає прогін.
    batched = _run_batch().timing
    stream, _ = _run_stream()
    assert f"{batched.first_audio:.0f}" in output, "числа батчу немає у виводі"
    assert f"{stream.timing.first_audio:.0f}" in output, "числа стрімінгу немає у виводі"

    for word in ("перекриття", "однаково", "p95", "ПЕРЕРВАТИ", "марна робота", "траєкторія"):
        assert word in output, f"сцена без {word!r}"

    # Дзеркальна половина сцени 5: у виводі є і «переривати», і «не переривати».
    assert output.count("не переривати") == 2 and "ПЕРЕРВАТИ" in output, (
        "barge-in показав не всі три рішення — а їх саме три, і в цьому урок"
    )

    # Сцена 4 має прогнати СПРАВЖНІ прогони, а не показати список, набраний руками.
    # Числа розподілу мають збігтися з тим, що дасть той самий прогін тут.
    from stages.s07_voice.run import RUNS

    values = [_run_batch(run=run).timing.first_audio for run in range(RUNS)]
    seen = summarise(values)
    assert f"{seen.p95:.0f}" in output and f"{seen.mean:.0f}" in output, (
        f"p95 {seen.p95:.0f} або середнє {seen.mean:.0f} у виводі не знайдено — сцена "
        "розподілу друкує не те, що дає прогін"
    )
    assert seen.worst > seen.p95 > seen.mean, (
        f"розподіл виродився: середнє {seen.mean:.0f}, p95 {seen.p95:.0f}, найгірший "
        f"{seen.worst:.0f}. Хвіст із одного ярусу робить p95 і найгірший одним числом, і "
        "різниця між «майже найгірший» і «найгірший» зникає саме там, де етап її показує"
    )


def check_the_demo_needs_no_microphone_models_or_network() -> None:
    """FAILURE · демо: жодної моделі, жодного мікрофона, жодної мережі"""
    source = (HERE / "run.py").read_text(encoding="utf-8")

    assert not code_mentions(source, {"faster_whisper", "piper", "socket", "requests"}), (
        "демо тягне модель або мережу. Правило курсу: усе працює офлайн — і найбільше це "
        "важить на етапі, де моделі важать гігабайти"
    )
    assert "FakeClock" in source, "демо не називає підробленого годинника явно"


# --- урок і матеріали читача -------------------------------------------------------------


def check_the_failure_modes_are_at_least_a_third() -> None:
    """перевірки: режимів відмови не менше третини (NFR-4)"""
    labels = [(c.__doc__ or "").split(NEWLINE)[0] for c in CHECKS]
    failures = [d for d in labels if d.startswith("FAILURE")]
    assert len(failures) * 3 >= len(CHECKS), (
        f"режимів відмови {len(failures)} із {len(CHECKS)} — менше третини"
    )


def check_the_lesson_fits_the_reading_budget() -> None:
    """урок: ≤2500 слів (NFR-3)"""
    words = len((HERE / "README.md").read_text(encoding="utf-8").split())
    assert words <= 2500, f"урок розрісся до {words} слів"


def check_the_lesson_numbers_match_the_suite() -> None:
    """FAILURE · урок: числа в прозі збігаються з тим, що друкує команда"""
    total = len(CHECKS)
    failures = sum(1 for c in CHECKS if (c.__doc__ or "").startswith("FAILURE"))
    sentence = f"{total} checks, {failures} of them on failure modes"
    for name in ("README.md", "CHECKLIST.md"):
        page = (HERE / name).read_text(encoding="utf-8")
        assert sentence in page, (
            f"{name} не містить рядка {sentence!r} — проза розійшлася з тим, що друкує "
            "команда, яку той самий урок наказує запустити"
        )


def check_the_lesson_numbers_match_the_measurements() -> None:
    """FAILURE · урок: числа конвеєра в прозі — обчислені, а не переписані"""
    # Ця перевірка стверджує про ПРОЗУ, а не про властивість. Під мутацією вона червоніє
    # від того, що числа перерахувались зі зламаного коду, — і «червоних 3» замість
    # «червоних 2» читається як «спіймали тричі». Три вправи з дванадцяти розходились із
    # `--expect` саме через це, і читач бачив червоне на першому ж кроці інструкції.
    for module in ("pipeline.py", "measure.py", "stt.py", "tts.py", "clock.py", "model.py"):
        require_intact_source(module)

    lesson = (HERE / "README.md").read_text(encoding="utf-8")

    batched = _run_batch().timing
    stream, _ = _run_stream()
    ratio = batched.first_audio / stream.timing.first_audio

    assert f"{batched.first_audio:.0f}" in lesson, "README.md: числа батчу немає"
    assert f"{stream.timing.first_audio:.0f}" in lesson, "README.md: числа стрімінгу немає"
    assert f"{ratio:.1f}" in lesson, f"README.md: відношення {ratio:.1f} немає"

    for step in batched.steps:
        assert f"{step.millis:.0f}" in lesson, f"кроку {step.name} немає в уроці"


def check_the_lesson_line_counts_match_the_modules() -> None:
    """FAILURE · урок: розмір `pipeline.py` у прозі — обчислений"""
    require_intact_source("pipeline.py")
    lines = _executable_lines("pipeline.py")
    lesson = (HERE / "README.md").read_text(encoding="utf-8")

    assert f"`pipeline.py` — {lines} of 110" in lesson, (
        f"pipeline.py має {lines} виконуваних рядків — урок називає інше число"
    )
    assert lines <= 110, f"{lines} > 110 (NFR-1)"


def check_the_exercises_match_the_pinned_mutations() -> None:
    """FAILURE · вправи: диф і числа беруться з mutations.json, а не пишуться"""
    import json

    pinned = json.loads((HERE / "mutations.json").read_text(encoding="utf-8"))["mutations"]
    text_of = (HERE / "exercises.md").read_text(encoding="utf-8")

    for mutation in pinned:
        number = int(mutation["name"].split()[1])
        expected = mutation["expect_failed"]
        assert f"## Exercise {number} ·" in text_of, f"вправи {number} немає в прозі"
        assert f"**Red: {expected}.**" in text_of, number
        for side in ("old", "new"):
            for line in mutation[side].split(NEWLINE):
                assert line.strip() in text_of, (
                    f"вправа {number}: рядка {line.strip()!r} немає в прозі — читач не "
                    "побачить, ЩО саме міняти"
                )

    assert text_of.count("## Exercise") == len(pinned), len(pinned)


def check_every_reader_file_exists() -> None:
    """матеріали: урок, карта, вправи, чеклісти й розвʼязок на місці"""
    for name in (
        "README.md",
        "exercises.md",
        "CHECKLIST.md",
        "DECISION.md",
        "page.html",
        "solutions/exercise_4_where_the_gain_lives.py",
        "solutions/README.md",
    ):
        path = HERE / name
        assert path.exists() and path.read_text(encoding="utf-8").strip(), name


def _executable_lines(name: str) -> int:
    """Виконувані рядки модуля: statement без docstring і без import."""
    import ast

    source = (HERE / name).read_text(encoding="utf-8")
    return len(
        {
            node.lineno
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.stmt)
            and not isinstance(node, (ast.Import, ast.ImportFrom))
            and not (
                isinstance(node, ast.Expr) and isinstance(getattr(node.value, "value", None), str)
            )
        }
    )


CHECKS = [
    check_the_batch_pipeline_reports_first_audio_and_its_parts,
    check_the_streaming_breakdown_adds_up_with_a_slow_consumer,
    check_an_unfinished_run_refuses_to_report_a_total,
    check_streaming_reaches_first_audio_at_least_twice_as_fast,
    check_the_total_duration_stays_about_the_same,
    check_every_stage_is_named_and_timed,
    check_p95_is_visibly_larger_than_the_mean,
    check_p95_keeps_its_promise_at_every_sample_size,
    check_a_distribution_of_nothing_is_refused,
    check_noise_does_not_interrupt,
    check_short_speech_does_not_interrupt,
    check_speech_does_interrupt_and_says_why,
    check_both_thresholds_actually_decide,
    check_prefetch_buys_a_measured_number_of_milliseconds,
    check_a_discarded_prefetch_does_not_delay_the_answer,
    check_an_unused_prefetch_is_named_as_wasted_work,
    check_empty_transcription_calls_neither_model_nor_synthesis,
    check_streaming_also_refuses_silence,
    check_a_model_that_says_nothing_is_not_reported_as_instant,
    check_the_chunks_refuse_a_second_walk,
    check_the_pipeline_never_reads_the_system_clock,
    check_two_runs_in_flight_do_not_corrupt_each_other,
    check_the_fake_clock_does_not_actually_sleep,
    check_the_clock_factory_defaults_to_fake,
    check_the_stopwatch_refuses_a_second_first_audio,
    check_the_microphone_needs_an_explicit_action,
    check_the_page_recovers_from_a_failure_after_permission,
    check_the_page_shows_what_actually_happened_not_what_it_intended,
    check_the_page_writes_down_numbers_and_nothing_else,
    check_a_missing_model_is_explained_not_crashed,
    check_the_live_mode_actually_exists_and_is_reachable,
    check_the_socket_reuses_the_pipeline_it_does_not_copy_it,
    check_the_trace_carries_the_same_breakdown_as_the_timing,
    check_the_socket_actually_runs_a_conversation,
    check_the_web_module_is_not_imported_on_a_bare_install,
    check_the_demo_shows_every_scene_with_real_numbers,
    check_the_demo_needs_no_microphone_models_or_network,
    check_the_failure_modes_are_at_least_a_third,
    check_the_lesson_fits_the_reading_budget,
    check_the_lesson_numbers_match_the_suite,
    check_the_lesson_numbers_match_the_measurements,
    check_the_lesson_line_counts_match_the_modules,
    check_the_exercises_match_the_pinned_mutations,
    check_every_reader_file_exists,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 7 · Voice")


if __name__ == "__main__":
    raise SystemExit(main())
