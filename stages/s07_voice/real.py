"""Справжні адаптери живого режиму: `faster-whisper` і `piper`.

    pip install -e ".[voice]"

**Цей файл — єдине місце етапу, яке автор не прогнав.** Моделі важать гігабайти, мікрофона
в перевірочній машині немає, і жодна перевірка тут нічого не доводить: AC-07 лишається
`НЕ ПЕРЕВІРЕНО` свідомо. Перша редакція етапу зробила гірше — просто не написала цього
файлу, лишивши `from stages.s07_voice.real import …` у двох фабриках. Читач, який виконав
задокументовану інструкцію й **встановив** пакети, отримував `ModuleNotFoundError` замість
голосу; читач, який їх не встановив, отримував ввічливе повідомлення. Тобто інструкція
карала за те, що їй підкорилися.

**Чому тут немає `clock`.** Підроблені адаптери сплять задану кількість мілісекунд; справжні
просто роблять роботу, а `RealClock` її міряє. Годинник лишається в сигнатурі, бо протокол
один на обидві реалізації, — але справжній адаптер його не чіпає.

**Моделі беруться з оточення**, а не з коду: розмір моделі й голос залежать від машини й
мови, і зашивати їх означало б ухвалювати за читача рішення, якого етап не пояснює.
"""

from __future__ import annotations

import io
import os
import wave
from typing import Any

from stages.s07_voice.clock import Clock
from stages.s07_voice.stt import Heard
from stages.s07_voice.tts import Spoken

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
PIPER_VOICE = os.getenv("PIPER_VOICE", "")


class RealRecogniser:
    """`faster-whisper` над семплами, що прийшли з браузера.

    Модель вантажиться **лениво**, при першому розпізнаванні: інакше імпорт модуля коштує
    гігабайт на машині, яка живого режиму й не вмикала.
    """

    name = f"faster-whisper:{WHISPER_MODEL}"

    def __init__(self) -> None:
        self._model: Any = None

    def _load(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel  # noqa: PLC0415 — лише за прапорцем

            self._model = WhisperModel(WHISPER_MODEL, compute_type="int8")
        return self._model

    def hear(self, audio: Any, *, clock: Clock) -> Heard:
        samples = getattr(audio, "samples", b"")
        if not samples:
            # Порожній кадр — це мовчання, а не помилка. Конвеєр зупиниться до моделі.
            return Heard(text="", seconds=getattr(audio, "seconds", 0.0))

        # `faster-whisper` декодує через ffmpeg, тож формат браузера (webm/opus) читається
        # так само, як wav. Семпли лишаються в памʼяті й на диск не потрапляють (AC-10b).
        segments, _ = self._load().transcribe(io.BytesIO(samples))
        text = "".join(segment.text for segment in segments)
        return Heard(text=text.strip(), seconds=getattr(audio, "seconds", 0.0))


class RealSynthesiser:
    """`piper` над фрагментом тексту. Віддає wav-байти разом із текстом."""

    name = "piper"

    def __init__(self) -> None:
        self._voice: Any = None

    def _load(self) -> Any:
        if self._voice is None:
            from piper import PiperVoice  # noqa: PLC0415 — лише за прапорцем

            if not PIPER_VOICE:
                raise RuntimeError(
                    "PIPER_VOICE не задано. Вкажи шлях до .onnx-голосу: "
                    "PIPER_VOICE=/шлях/до/voice.onnx — і перезапусти"
                )
            self._voice = PiperVoice.load(PIPER_VOICE)
        return self._voice

    def say(self, text: str, *, clock: Clock) -> Spoken:
        started = clock.now()
        buffer = io.BytesIO()
        voice = self._load()
        with wave.open(buffer, "wb") as handle:
            voice.synthesize(text, handle)
        return Spoken(text=text, millis=clock.now() - started, audio=buffer.getvalue())
