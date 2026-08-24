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
ANSWER = "Замовлення в дорозі. Очікуйте доставку завтра до вечора."
CHUNKS = ["Замовлення в дорозі.", " Очікуйте доставку", " завтра до вечора."]


# Затримки навмисно РІЗНІ: інакше «найдорожчий крок» стає жеребкуванням між
# рівними, і питання «що оптимізувати першим» лишається без відповіді.
THINK_MILLIS = 750.0


def _think(_: str, *, clock) -> str:
    """Підроблена модель: пише всю відповідь одразу, витративши правдоподібний час."""
    clock.sleep(THINK_MILLIS)
    return ANSWER


def _think_chunks(_: str, *, clock):
    """Та сама модель, але фрагментами. **Сума затримок однакова** — це навмисно.

    Інакше стрімінг виглядав би швидшим тому, що йому дали менше роботи, і число нічого б не
    доводило.
    """
    for chunk in CHUNKS:
        clock.sleep(THINK_MILLIS / len(CHUNKS))
        yield chunk


def _run_batch(clock=None):
    clock = clock or FakeClock()
    return batch(SAID, clock=clock, stt=FakeRecogniser(), tts=FakeSynthesiser(), think=_think)


def _run_stream(clock=None):
    clock = clock or FakeClock()
    stream = streaming(
        SAID,
        clock=clock,
        # Стрімінгове розпізнавання — не дрібниця, а найбільший внесок у різницю:
        # воно йде РАЗОМ із мовленням, тож до кінця фрази лишається дописати хвіст.
        stt=FakeRecogniser(incremental=True),
        tts=FakeSynthesiser(),
        think_chunks=_think_chunks,
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
    parts = sum(step.millis for step in timing.steps)
    assert abs(parts - timing.total) < 0.001, (parts, timing.total)
    assert abs(timing.first_audio - timing.total) < 0.001, (
        "у батчевому конвеєрі перший звук збігається із завершенням: синтез не може почати, "
        "доки модель не дописала останнє слово"
    )


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
    """ВІДМОВА · раніша віддача НЕ зменшує роботи — виграш має дві різні частини"""
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
    """ВІДМОВА · розподіл: p95 помітно більший за середнє — звітують не тим числом"""
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


def check_a_distribution_of_nothing_is_refused() -> None:
    """ВІДМОВА · розподіл із нуля прогонів — помилка, а не нулі"""
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
    """ВІДМОВА · barge-in: тихий звук не перериває відповідь"""
    decision = should_interrupt(Sound(level=0.1, millis=100.0))

    assert not decision.interrupt, decision
    assert QUIET in decision.reason, decision.reason


def check_short_speech_does_not_interrupt() -> None:
    """ВІДМОВА · barge-in: гучний, але короткий звук не перериває — умов дві"""
    decision = should_interrupt(Sound(level=0.9, millis=80.0))

    assert not decision.interrupt, (
        "клацання мишею перервало відповідь. Рівня самого недосить: детектор, що дивиться "
        "лише на гучність, перериває від кашлю й стуку клавіш"
    )
    assert SHORT in decision.reason, decision.reason


def check_speech_does_interrupt_and_says_why() -> None:
    """ВІДМОВА · дзеркальна: мовлення таки перериває — детектор не глухий"""
    decision = should_interrupt(Sound(level=0.9, millis=300.0))

    assert decision.interrupt, (
        "мовлення не перервало відповідь. Детектор, що не перериває ніколи, задовольняє "
        "обидві перевірки вище повністю й при цьому зламаний"
    )
    assert SPEECH in decision.reason and str(int(MIN_SPEECH_MILLIS)) in decision.reason


def check_both_thresholds_actually_decide() -> None:
    """ВІДМОВА · barge-in: кожна з двох умов справді впливає на рішення"""
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
    """prefetch: виграш названо числом, а не словом «швидше»"""
    calls: list[str] = []

    def tool() -> None:
        calls.append("called")

    slow = synchronous(tool, clock=FakeClock(), needed=True, tool_millis=500.0)
    fast = prefetched(tool, clock=FakeClock(), needed=True, tool_millis=500.0, think_millis=600.0)

    assert len(calls) == 2, calls
    bought = slow.millis + 600.0 - fast.millis
    assert bought > 0, (
        f"prefetch не купив нічого: синхронно {slow.millis:.0f} мс, з prefetch "
        f"{fast.millis:.0f} мс. Тоді складність додано за нуль"
    )
    assert fast.millis == 600.0, fast


def check_an_unused_prefetch_is_named_as_wasted_work() -> None:
    """ВІДМОВА · prefetch: непотрібний виклик відбувся, і це названо марною роботою"""
    calls: list[str] = []
    outcome = prefetched(
        lambda: calls.append("called"),
        clock=FakeClock(),
        needed=False,
        tool_millis=500.0,
        think_millis=600.0,
    )

    assert calls == ["called"], "prefetch не покликав інструмент — тоді він нічого не купує"
    assert not outcome.used, outcome
    assert WASTED in outcome.note, (
        f"марну роботу не названо: {outcome.note!r}. Prefetch виконує виклик, який може не "
        "знадобитись — етап, що показує лише виграш, агітує, а не вчить"
    )

    # Дзеркальна половина: коли інструмент таки потрібен, марної роботи немає.
    used = prefetched(
        lambda: None, clock=FakeClock(), needed=True, tool_millis=500.0, think_millis=600.0
    )
    assert used.used and not used.note, used


# --- мовчання ---------------------------------------------------------------------------


def check_empty_transcription_calls_neither_model_nor_synthesis() -> None:
    """ВІДМОВА · мовчання — не запит: ані модель, ані синтез не викликаються"""
    clock = FakeClock()
    reply = batch(
        Audio(seconds=1.0, says="   "),
        clock=clock,
        stt=FakeRecogniser(),
        tts=FakeSynthesiser(),
        think=_think,
    )

    assert reply.silent and reply.said == "", reply
    assert [step.name for step in reply.timing.steps] == [STT, SILENT], reply.timing.as_rows()
    # Доказ не в іменах кроків, а в **затратах**: підроблена модель спить 600 мс, синтез —
    # пропорційно довжині. Якби їх покликали, годинник це показав би.
    assert clock.waits == [FakeRecogniser().millis_per_second * 1.0], clock.waits


def check_streaming_also_refuses_silence() -> None:
    """ВІДМОВА · мовчання зупиняє й стрімінговий конвеєр — обидва, не один"""
    clock = FakeClock()
    stream = streaming(
        Audio(seconds=1.0, says=""),
        clock=clock,
        stt=FakeRecogniser(),
        tts=FakeSynthesiser(),
        think_chunks=_think_chunks,
    )

    assert stream.silent and list(stream.chunks) == [], stream
    assert len(clock.waits) == 1, clock.waits


# --- годинник ---------------------------------------------------------------------------


def check_the_pipeline_never_reads_the_system_clock() -> None:
    """ВІДМОВА · годинник: конвеєр не кличе `time` — інакше перевірки мигтітимуть"""
    here = Path(__file__).parent
    for name in ("pipeline.py", "measure.py", "bargein.py", "prefetch.py", "stt.py", "tts.py"):
        source = (here / name).read_text(encoding="utf-8")
        found = code_mentions(source, {"perf_counter", "monotonic", "time.time"})
        assert not found, (
            f"{name} читає системний годинник: {found}. Тоді перевірка часу залежить від "
            "навантаження машини, падає раз на десять прогонів — і її вимикають разом із "
            "єдиним доказом головної тези етапу"
        )


def check_the_same_run_gives_the_same_number_twenty_times() -> None:
    """ВІДМОВА · мигтіння: двадцять прогонів поспіль дають однакове число (NFR-6)"""
    seen = {_run_batch().timing.first_audio for _ in range(20)}

    assert len(seen) == 1, (
        f"двадцять прогонів дали {len(seen)} різних чисел: {sorted(seen)}. Мигтлива "
        "перевірка гірша за відсутню: відсутню видно, мигтливу вимикають"
    )

    streamed = {_run_stream()[0].timing.first_audio for _ in range(20)}
    assert len(streamed) == 1, sorted(streamed)


def check_the_fake_clock_does_not_actually_sleep() -> None:
    """ВІДМОВА · підроблений годинник не спить — інакше двадцять прогонів коштували б хвилини"""
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
    """ВІДМОВА · фабрика: дефолт — підробка; справжній годинник лише за прапорцем"""
    assert isinstance(get_clock(), FakeClock), type(get_clock())
    assert isinstance(get_clock(real=True), RealClock), type(get_clock(real=True))

    # І дзеркально: справжній годинник справді рухається сам.
    real = RealClock()
    assert real.now() > 0


def check_the_stopwatch_refuses_a_second_first_audio() -> None:
    """ВІДМОВА · секундомір: перший звук позначається один раз"""
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


def check_the_microphone_needs_an_explicit_action() -> None:
    """ВІДМОВА · сторінка: мікрофон береться лише після натискання, і зупинка звільняє"""
    page = PAGE.read_text(encoding="utf-8")

    # `getUserMedia` має бути **всередині** обробника, а не на рівні модуля скрипта.
    # Сторінка, що бере мікрофон при завантаженні, порушує згоду незалежно від того, що
    # робить зі звуком далі.
    before, _, after = page.partition("getUserMedia")
    assert "addEventListener" in after or "async function start" in before, (
        "getUserMedia викликається поза обробником — мікрофон береться при завантаженні"
    )
    assert "async function start" in page and "getUserMedia" in page, page[:200]

    # Дзеркальна половина: пристрій звільняється. Червона крапка, що лишається горіти після
    # переходу на іншу сторінку, — це не косметика, це недотримана обіцянка.
    assert "getTracks().forEach" in page and "track.stop()" in page, (
        "доріжки не зупиняються — мікрофон лишається зайнятим після зупинки"
    )
    assert "pagehide" in page, "закриття вкладки не звільняє пристрій"


def check_the_page_writes_down_numbers_and_nothing_else() -> None:
    """ВІДМОВА · сеанс лишає числа — і не лишає ані семплів, ані тексту"""
    page = PAGE.read_text(encoding="utf-8")
    socket = (HERE / "ws.py").read_text(encoding="utf-8")

    # Ані сторінка, ані сокет не мають писати звук чи текст у сховище.
    for name, source in (("page.html", page), ("ws.py", socket)):
        for forbidden in ("localStorage", "indexedDB", "write_bytes", "open(", "wav"):
            if forbidden == "open(" and name == "page.html":
                continue
            assert forbidden not in source or forbidden == "wav", (
                f"{name} зберігає щось із сеансу: {forbidden!r}"
            )

    # Дзеркальна половина: числа таки лишаються. Сеанс, що не лишає нічого, задовольняє
    # «звук не зберігається» повністю й робить етап невимірюваним.
    assert "first_audio" in socket and "as_rows" in socket, (
        "сокет не віддає розкладу — тоді сторінка не може показати ті самі числа, що прогін"
    )


def check_a_missing_model_is_explained_not_crashed() -> None:
    """ВІДМОВА · відсутня модель: сказано, що встановити, а не технічна помилка"""
    absent = missing_models()
    assert absent is None or absent == MISSING, absent

    # Повідомлення має містити КОМАНДУ. Читач, який бачить `ModuleNotFoundError`,
    # дізнається менше, ніж читач, який бачить, що набрати.
    assert "pip install" in MISSING, MISSING
    assert "ModuleNotFoundError" not in MISSING, MISSING
    # І має сказати, що працює без моделей: інакше читач вирішить, що етап зламався.
    assert "run" in MISSING, MISSING


def check_the_socket_reuses_the_pipeline_it_does_not_copy_it() -> None:
    """ВІДМОВА · сокет бере ТОЙ САМИЙ конвеєр — інакше числа розійдуться (AC-11)"""
    socket = (HERE / "ws.py").read_text(encoding="utf-8")

    assert "from stages.s07_voice.pipeline import" in socket, (
        "сокет не імпортує конвеєра. Власна копія кроків означає, що числа на сторінці й "
        "числа у прогоні можуть розійтися, і жодне не перевіряється другим"
    )
    # І не має власних затримок: усе, що спить, живе в адаптерах.
    assert not code_mentions(socket, {"sleep"}) or "clock.sleep" in socket, socket[:120]


def check_the_web_module_is_not_imported_on_a_bare_install() -> None:
    """ВІДМОВА · перевірки не тягнуть веб-фреймворк — інакше базова установка червоніє"""
    import ast

    # Розбір ІМПОРТІВ, а не пошук у тексті. Перша редакція шукала рядок
    # «...import create_app» — і знаходила його у власному ж повідомленні про помилку.
    # Пʼятий випадок цієї пастки в курсі: перевірка про код має дивитись на код.
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "stages.s07_voice.ws"
        for alias in node.names
    }
    assert "create_app" not in imported, (
        f"перевірки імпортують {sorted(imported)} — `create_app` тягне веб-фреймворк, "
        "і на базовій установці це червоне замість «не перевірено»"
    )
    # Дзеркальна половина: щось із `ws` імпортувати таки треба, інакше перевірка
    # відсутньої моделі нічого не перевіряє.
    assert "missing_models" in imported, imported


# --- e2e: демо ------------------------------------------------------------------------------


def check_the_demo_shows_six_scenes_with_real_numbers() -> None:
    """e2e · демо показує шість сцен, обидва числа й обидві частини виграшу"""
    import io
    from contextlib import redirect_stdout

    from stages.s07_voice.run import main as demo_main

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = demo_main()
    output = buffer.getvalue()

    assert code == 0, code
    assert output.startswith("[FakeClock]"), output.splitlines()[0]
    for number in range(1, 7):
        assert f"{NEWLINE}{number}. " in output, f"сцена {number} не надрукувалась"

    # Тіла сцен, а не заголовки. Числа мають бути ті самі, що дає прогін.
    batched = _run_batch().timing
    stream, _ = _run_stream()
    assert f"{batched.first_audio:.0f}" in output, "числа батчу немає у виводі"
    assert f"{stream.timing.first_audio:.0f}" in output, "числа стрімінгу немає у виводі"

    for word in ("перекриття", "однаково", "p95", "ПЕРЕРВАТИ", "марна робота"):
        assert word in output, f"сцена без {word!r}"

    # Дзеркальна половина сцени 5: у виводі є і «переривати», і «не переривати».
    assert output.count("не переривати") == 2 and "ПЕРЕРВАТИ" in output, (
        "barge-in показав не всі три рішення — а їх саме три, і в цьому урок"
    )


def check_the_demo_needs_no_microphone_models_or_network() -> None:
    """ВІДМОВА · демо: жодної моделі, жодного мікрофона, жодної мережі"""
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
    failures = [d for d in labels if d.startswith("ВІДМОВА")]
    assert len(failures) * 3 >= len(CHECKS), (
        f"режимів відмови {len(failures)} із {len(CHECKS)} — менше третини"
    )


def check_the_lesson_fits_the_reading_budget() -> None:
    """урок: ≤2500 слів (NFR-3)"""
    words = len((HERE / "README.md").read_text(encoding="utf-8").split())
    assert words <= 2500, f"урок розрісся до {words} слів"


def check_the_lesson_numbers_match_the_suite() -> None:
    """ВІДМОВА · урок: числа в прозі збігаються з тим, що друкує команда"""
    total = len(CHECKS)
    failures = sum(1 for c in CHECKS if (c.__doc__ or "").startswith("ВІДМОВА"))
    for name, sentence in (
        ("README.md", f"перевірок: {total}, з них на режими відмови: {failures}"),
        ("CHECKLIST.md", f"перевірок: {total}, з них на режими відмови: {failures}"),
        ("README.en.md", f"{total} checks, {failures} of them on failure modes"),
    ):
        page = (HERE / name).read_text(encoding="utf-8")
        assert sentence in page, (
            f"{name} не містить рядка {sentence!r} — проза розійшлася з тим, що друкує "
            "команда, яку той самий урок наказує запустити"
        )


def check_the_lesson_numbers_match_the_measurements() -> None:
    """ВІДМОВА · урок: числа конвеєра в прозі — обчислені, а не переписані"""
    lesson = (HERE / "README.md").read_text(encoding="utf-8")
    english = (HERE / "README.en.md").read_text(encoding="utf-8")

    batched = _run_batch().timing
    stream, _ = _run_stream()
    ratio = batched.first_audio / stream.timing.first_audio

    for page, name in ((lesson, "README.md"), (english, "README.en.md")):
        assert f"{batched.first_audio:.0f}" in page, f"{name}: числа батчу немає"
        assert f"{stream.timing.first_audio:.0f}" in page, f"{name}: числа стрімінгу немає"
        assert f"{ratio:.1f}" in page, f"{name}: відношення {ratio:.1f} немає"

    for step in batched.steps:
        assert f"{step.millis:.0f}" in lesson, f"кроку {step.name} немає в уроці"


def check_the_lesson_line_counts_match_the_modules() -> None:
    """ВІДМОВА · урок: розмір `pipeline.py` у прозі — обчислений"""
    require_intact_source("pipeline.py")
    lines = _executable_lines("pipeline.py")
    lesson = (HERE / "README.md").read_text(encoding="utf-8")

    assert f"`pipeline.py` — {lines} із 110" in lesson, (
        f"pipeline.py має {lines} виконуваних рядків — урок називає інше число"
    )
    assert lines <= 110, f"{lines} > 110 (NFR-1)"


def check_the_exercises_match_the_pinned_mutations() -> None:
    """ВІДМОВА · вправи: диф і числа беруться з mutations.json, а не пишуться"""
    import json

    pinned = json.loads((HERE / "mutations.json").read_text(encoding="utf-8"))["mutations"]
    text_of = (HERE / "exercises.md").read_text(encoding="utf-8")

    for mutation in pinned:
        number = int(mutation["name"].split()[1])
        expected = mutation["expect_failed"]
        assert f"## Вправа {number} ·" in text_of, f"вправи {number} немає в прозі"
        assert f"**Червоних: {expected}.**" in text_of, number
        for side in ("old", "new"):
            for line in mutation[side].split(NEWLINE):
                assert line.strip() in text_of, (
                    f"вправа {number}: рядка {line.strip()!r} немає в прозі — читач не "
                    "побачить, ЩО саме міняти"
                )

    assert text_of.count("## Вправа") == len(pinned), len(pinned)


def check_every_reader_file_exists() -> None:
    """матеріали: урок, карта, вправи, чеклісти й розвʼязок на місці"""
    for name in (
        "README.md",
        "README.en.md",
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
    check_streaming_reaches_first_audio_at_least_twice_as_fast,
    check_the_total_duration_stays_about_the_same,
    check_every_stage_is_named_and_timed,
    check_p95_is_visibly_larger_than_the_mean,
    check_a_distribution_of_nothing_is_refused,
    check_noise_does_not_interrupt,
    check_short_speech_does_not_interrupt,
    check_speech_does_interrupt_and_says_why,
    check_both_thresholds_actually_decide,
    check_prefetch_buys_a_measured_number_of_milliseconds,
    check_an_unused_prefetch_is_named_as_wasted_work,
    check_empty_transcription_calls_neither_model_nor_synthesis,
    check_streaming_also_refuses_silence,
    check_the_pipeline_never_reads_the_system_clock,
    check_the_same_run_gives_the_same_number_twenty_times,
    check_the_fake_clock_does_not_actually_sleep,
    check_the_clock_factory_defaults_to_fake,
    check_the_stopwatch_refuses_a_second_first_audio,
    check_the_microphone_needs_an_explicit_action,
    check_the_page_writes_down_numbers_and_nothing_else,
    check_a_missing_model_is_explained_not_crashed,
    check_the_socket_reuses_the_pipeline_it_does_not_copy_it,
    check_the_web_module_is_not_imported_on_a_bare_install,
    check_the_demo_shows_six_scenes_with_real_numbers,
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
