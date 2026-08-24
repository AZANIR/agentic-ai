"""Живий режим: сторінка, сокет і **той самий** конвеєр.

Транспорт інший, конвеєр той самий — це не економія, а вимога. Якби сокет мав власну копію
кроків, числа на сторінці й числа у прогоні розходились би, і жодне з них не можна було б
перевірити другим (AC-11).

**Модуль імпортується лише тоді, коли живий режим потрібен.** Він тягне веб-фреймворк, а
етап має проходитись на базовій установці — тож перевірки читають цей файл, а не імпортують
його (урок етапу 6).

**Конвеєр синхронний, обробник — ні.** Справжні адаптери працюють секундами, і виконати їх
просто в корутині означає заморозити event loop: дві одночасні розмови серіалізуються, а
750 мс роздуму одного клієнта — це 750 мс тиші для всіх інших на тому ж воркері. Урок
етапу 6 про це саме, тож кожен фрагмент береться в потоці.

**Чого тут немає:** запису звуку на диск, зберігання розпізнаного тексту й будь-якої адреси,
крім власної. Сеанс лишає по собі **числа** — і нічого більше (AC-10b).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from stages.s07_voice.clock import get_clock
from stages.s07_voice.model import in_chunks
from stages.s07_voice.pipeline import Audio, streaming
from stages.s07_voice.stt import get_recogniser
from stages.s07_voice.tts import get_synthesiser

PAGE = Path(__file__).parent / "page.html"

# Скільки звуку в одному кадрі. Сторінка каже це першим повідомленням: вивести тривалість
# із довжини кадру неможливо, бо MediaRecorder віддає **стиснутий** opus/webm, і
# `len(chunk) / 32_000` дало б 25 мс замість 200. Перша редакція так і рахувала, і крок
# «розпізнавання» виходив 8 мс замість 600 — при тому, що сторінка обіцяла ті самі числа,
# що й прогін.
DEFAULT_FRAME_SECONDS = 0.2

# Що «почула» підробка. Розпізнавати їй нічим, і мовчати вона теж не може: порожній текст
# зупинив би конвеєр як мовчання (AC-09), і сторінка без моделей не показала б нічого.
# Стенд-ін названий стенд-іном — щоб ніхто не вирішив, що це розпізнавання.
FAKE_TRANSCRIPT = "(підроблене розпізнавання — моделей немає)"

MISSING = (
    "Голосові моделі не встановлено. Сторінка працює, конвеєр працює, звуку не буде.\n"
    'Встанови: pip install -e ".[voice]" — і перезапусти.\n'
    "Числа у прогоні `python -m stages.s07_voice.run` доступні й без них."
)

VOICE_MODULES = ("faster_whisper", "piper", "stages.s07_voice.real")


def missing_models(modules: tuple[str, ...] = VOICE_MODULES) -> str | None:
    """Чого бракує для живого режиму. `None`, коли все на місці (AC-07b).

    Повідомлення каже, **що встановити**, а не яка бібліотека не знайшлась. Читач, який
    бачить `ModuleNotFoundError: faster_whisper`, дізнається менше, ніж читач, який бачить
    команду.

    Перелік модулів — параметр, і не заради гнучкості: без нього перевірка могла пройти
    лише ту гілку, яка справджується на машині, де її запустили. Гілка «моделі на місці»
    не виконувалась ніде — а вона й була зламана.
    """
    for module in modules:
        try:
            __import__(module)
        except ImportError:
            return MISSING
    return None


def create_app(*, real: bool = False) -> Any:
    """Застосунок живого режиму: сторінка й сокет. Нічого не вирішує сам."""
    import anyio  # noqa: PLC0415
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: PLC0415
    from fastapi.responses import HTMLResponse  # noqa: PLC0415

    app = FastAPI(title="s07 voice", docs_url=None, redoc_url=None)
    absent = missing_models() if real else None

    @app.get("/", response_class=HTMLResponse)
    def page():
        return HTMLResponse(PAGE.read_text(encoding="utf-8"))

    async def voice(socket) -> None:
        await socket.accept()
        if absent:
            await socket.send_json({"kind": "missing", "text": absent})
            await socket.close()
            return

        clock = get_clock(real=real)
        frame_seconds = DEFAULT_FRAME_SECONDS
        try:
            stt, tts = get_recogniser(real=real), get_synthesiser(real=real)
        except Exception as error:  # noqa: BLE001 — будь-яка причина, одне повідомлення
            # Пакети є, але адаптер не піднявся: немає ваг, не заданий голос, не та версія.
            # Читач має побачити, що робити, а не трейсбек у логах сервера.
            await socket.send_json({"kind": "missing", "text": f"{MISSING}\n\n{error}"})
            await socket.close()
            return

        frames: list[bytes] = []
        seconds = 0.0
        try:
            while True:
                message = await socket.receive()
                if message.get("bytes") is not None:
                    # Кадри НАКОПИЧУЮТЬСЯ. Запускати конвеєр на кожні 200 мс означало б
                    # пʼять відповідей на секунду — і, головне, міряти не те: час до
                    # першого звуку рахується **від кінця репліки**, тож поки людина
                    # говорить, кінця ще немає.
                    frames.append(message["bytes"])
                    seconds += frame_seconds
                    continue
                if message.get("text") is None:
                    return  # відключення

                note = _note(message["text"])
                if "seconds" in note:
                    frame_seconds = _positive(note["seconds"], frame_seconds)
                    continue
                if not note.get("end") or not frames:
                    continue

                # Репліка скінчилась — ось тепер конвеєр. Семпли йдуть у розпізнавання й
                # нікуди більше: ані на диск, ані у трейс.
                # Справжнє розпізнавання читає семпли; підробці читати нічим, тож їй
                # дається стенд-ін. Порожній текст зупинив би конвеєр як мовчання.
                heard_by_fake = "" if real else FAKE_TRANSCRIPT
                said = Audio(seconds=seconds, says=heard_by_fake, samples=b"".join(frames))
                frames, seconds = [], 0.0
                stream = streaming(said, clock=clock, stt=stt, tts=tts, think_chunks=in_chunks())
                walk = iter(stream.chunks)
                while True:
                    # Крок конвеєра — у потоці. Інакше синхронний `clock.sleep` під
                    # `RealClock` тримає event loop і всі інші розмови стоять.
                    spoken = await anyio.to_thread.run_sync(next, walk, None)
                    if spoken is None:
                        break
                    await socket.send_json(_chunk_message(spoken))
                await socket.send_json(_timing_message(stream.timing))
        except WebSocketDisconnect:
            # Вкладку закрили. Це не помилка — це кінець сеансу, і нічого прибирати не
            # треба: стану, який пережив би зʼєднання, тут немає навмисно.
            return

    # Тип сокета проставляється ТУТ, а не анотацією.
    #
    # `from __future__ import annotations` робить усі анотації рядками, а `WebSocket`
    # імпортовано **всередині** цієї функції — тож у глобальному просторі модуля його
    # немає, і FastAPI розвʼязати імʼя не може. Замість помилки він робить розумну річ:
    # вважає `socket` звичайним query-параметром. Кожне зʼєднання закривалося з кодом
    # 1008 «Field required» **до** `accept()`, тобто живий режим не працював ніколи —
    # ані зі справжніми моделями, ані з підробленими.
    #
    # Знайшлось це не читанням: два рев'юери прочитали цей файл і не побачили нічого.
    # Знайшлось першим запуском. Тому нижче в наборі є перевірка, яка сокет **виконує**.
    voice.__annotations__ = {"socket": WebSocket, "return": None}
    app.websocket("/voice")(voice)

    return app


def create_real_app() -> Any:
    """Живий режим одним іменем — бо `--factory` не вміє передавати аргументів.

    Задокументована команда етапу раніше вела на `create_app`, тобто на `real=False`:
    вона піднімала підроблені адаптери й підроблений годинник, а поруч просила встановити
    гігабайти моделей, які цим шляхом не використовувались жодного разу.
    """
    return create_app(real=True)


def _note(raw: str) -> dict[str, Any]:
    """Службове повідомлення сторінки. Нерозбірливе — не привід падати."""
    import json  # noqa: PLC0415

    try:
        note = json.loads(raw)
    except ValueError:
        return {}
    return note if isinstance(note, dict) else {}


def _positive(value: Any, fallback: float) -> float:
    """Додатне число або те, що було. Нуль тривалості кадру знищив би весь розклад."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if number > 0 else fallback


def _chunk_message(spoken: Any) -> dict[str, Any]:
    import base64  # noqa: PLC0415

    message: dict[str, Any] = {"kind": "chunk", "text": spoken.text}
    if spoken.audio:
        message["audio"] = base64.b64encode(spoken.audio).decode("ascii")
    return message


def _timing_message(timing: Any) -> dict[str, Any]:
    """Розклад для сторінки. `first_audio` може бути `None` — і це не нуль.

    Порожня відповідь моделі лишає перший звук непозначеним. Перша редакція писала тут
    `or 0.0`, і сторінка показувала «до першого звуку: 0 мс» — найкращу можливу затримку
    для прогону, у якому звуку не було взагалі.
    """
    return {
        "kind": "timing",
        "timing": {
            "steps": timing.as_rows(),
            "first_audio": timing.first_audio,
            "handover": timing.handover,
            "total": timing.total,
        },
    }
