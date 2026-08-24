"""Живий режим: сторінка, сокет і **той самий** конвеєр.

Транспорт інший, конвеєр той самий — це не економія, а вимога. Якби сокет мав власну копію
кроків, числа на сторінці й числа у прогоні розходились би, і жодне з них не можна було б
перевірити другим (AC-11).

**Модуль імпортується лише тоді, коли живий режим потрібен.** Він тягне веб-фреймворк, а
етап має проходитись на базовій установці — тож перевірки читають цей файл, а не імпортують
його (урок етапу 6).

**Чого тут немає:** запису звуку на диск, зберігання розпізнаного тексту й будь-якої адреси,
крім власної. Сеанс лишає по собі **числа** — і нічого більше (AC-10b).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from stages.s07_voice.clock import get_clock
from stages.s07_voice.pipeline import Audio, streaming
from stages.s07_voice.stt import get_recogniser
from stages.s07_voice.tts import get_synthesiser

PAGE = Path(__file__).parent / "page.html"

MISSING = (
    "Голосові моделі не встановлено. Сторінка працює, конвеєр працює, звуку не буде.\n"
    'Встанови: pip install -e ".[voice]" — і перезапусти.\n'
    "Числа у прогоні `python -m stages.s07_voice.run` доступні й без них."
)


def missing_models() -> str | None:
    """Чого бракує для живого режиму. `None`, коли все на місці (AC-07b).

    Повідомлення каже, **що встановити**, а не яка бібліотека не знайшлась. Читач, який
    бачить `ModuleNotFoundError: faster_whisper`, дізнається менше, ніж читач, який бачить
    команду.
    """
    for module in ("faster_whisper", "piper"):
        try:
            __import__(module)
        except ImportError:
            return MISSING
    return None


def create_app(*, real: bool = False) -> Any:
    """Застосунок живого режиму: сторінка й сокет. Нічого не вирішує сам."""
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: PLC0415
    from fastapi.responses import HTMLResponse  # noqa: PLC0415

    app = FastAPI(title="s07 voice", docs_url=None, redoc_url=None)
    absent = missing_models() if real else None

    @app.get("/")
    def page() -> HTMLResponse:
        return HTMLResponse(PAGE.read_text(encoding="utf-8"))

    @app.websocket("/voice")
    async def voice(socket: WebSocket) -> None:
        await socket.accept()
        if absent:
            await socket.send_json({"kind": "missing", "text": absent})
            await socket.close()
            return

        clock = get_clock(real=real)
        try:
            while True:
                chunk = await socket.receive_bytes()
                # Тривалість — усе, що потрібно конвеєру від семплів. Самі семпли далі не
                # йдуть і нікуди не пишуться.
                said = Audio(seconds=len(chunk) / 32_000, says="…")
                stream = streaming(
                    said,
                    clock=clock,
                    stt=get_recogniser(real=real),
                    tts=get_synthesiser(real=real),
                    think_chunks=_chunks,
                )
                for spoken in stream.chunks:
                    await socket.send_json({"kind": "chunk", "text": spoken.text})
                await socket.send_json(
                    {
                        "kind": "timing",
                        "timing": {
                            "steps": stream.timing.as_rows(),
                            "first_audio": stream.timing.first_audio or 0.0,
                        },
                    }
                )
        except WebSocketDisconnect:
            # Вкладку закрили. Це не помилка — це кінець сеансу, і нічого прибирати не
            # треба: стану, який пережив би зʼєднання, тут немає навмисно.
            return

    return app


def _chunks(_: str, *, clock: Any):
    for part in ("Слухаю.", " Зараз перевірю."):
        clock.sleep(250.0)
        yield part
