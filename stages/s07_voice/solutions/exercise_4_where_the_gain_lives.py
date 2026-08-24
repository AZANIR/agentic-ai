"""Звідки насправді береться виграш — на репліках різної довжини.

    python -m stages.s07_voice.solutions.exercise_4_where_the_gain_lives

Червона перевірка вправи 4 каже «відношення впало нижче двох». Вона не показує **чому** —
а причина найцікавіша в усьому етапі.

Виграш стрімінгу складається з двох частин, і вони поводяться по-різному, коли людина
говорить довше. Побачити це можна лише поставивши кілька довжин поруч.
"""

from __future__ import annotations

from dataclasses import dataclass

from stages.s07_voice.clock import FakeClock
from stages.s07_voice.pipeline import SPEAK, STT, THINK, Audio, batch, streaming
from stages.s07_voice.stt import FakeRecogniser
from stages.s07_voice.tts import FakeSynthesiser

ANSWER = "Замовлення в дорозі. Очікуйте доставку завтра до вечора."
CHUNKS = ["Замовлення в дорозі.", " Очікуйте доставку", " завтра до вечора."]
THINK_MILLIS = 750.0
LENGTHS = (1.0, 2.0, 5.0, 10.0)


def _think(_: str, *, clock) -> str:
    clock.sleep(THINK_MILLIS)
    return ANSWER


def _think_chunks(_: str, *, clock):
    for chunk in CHUNKS:
        clock.sleep(THINK_MILLIS / len(CHUNKS))
        yield chunk


@dataclass
class Row:
    seconds: float
    batch_first: float
    stream_first: float
    overlap: float
    delivery: float

    @property
    def ratio(self) -> float:
        return self.batch_first / self.stream_first


def measure(seconds: float) -> Row:
    said = Audio(seconds=seconds, says="який статус мого замовлення")

    batched = batch(
        said, clock=FakeClock(), stt=FakeRecogniser(), tts=FakeSynthesiser(), think=_think
    ).timing

    stream = streaming(
        said,
        clock=FakeClock(),
        stt=FakeRecogniser(incremental=True),
        tts=FakeSynthesiser(),
        think_chunks=_think_chunks,
    )
    list(stream.chunks)

    # Дві частини виграшу, розділені явно.
    overlap = batched.named(STT) - stream.timing.named(STT)
    answer_batch = batched.named(THINK) + batched.named(SPEAK)
    delivery = answer_batch - (stream.timing.first_audio - stream.timing.named(STT))

    return Row(
        seconds=seconds,
        batch_first=batched.first_audio,
        stream_first=stream.timing.first_audio,
        overlap=overlap,
        delivery=delivery,
    )


def main() -> int:
    print("Та сама відповідь, репліки різної довжини.")
    print()
    print(f"  {'репліка':>8} {'батч':>8} {'стрім':>8} {'x':>6} {'перекриття':>12} {'віддача':>9}")
    rows = [measure(seconds) for seconds in LENGTHS]
    for row in rows:
        print(
            f"  {row.seconds:>6.0f} с {row.batch_first:>7.0f} {row.stream_first:>8.0f}"
            f" {row.ratio:>6.1f} {row.overlap:>12.0f} {row.delivery:>9.0f}"
        )
    print()

    first, last = rows[0], rows[-1]
    print("Що тут читати:")
    print()
    print(f"  **Перекриття** росте з довжиною репліки: {first.overlap:.0f} мс на одній секунді,")
    print(f"  {last.overlap:.0f} мс на десяти. Розпізнавання йде разом із мовленням, тож що")
    print("  довше людина говорить, то більше роботи встигає статися до її паузи.")
    print()
    print(f"  **Раніша віддача** не змінюється взагалі: {first.delivery:.0f} мс на будь-якій")
    print("  довжині. Вона не залежить від репліки — лише від того, як швидко модель напише")
    print("  перший фрагмент.")
    print()
    print(f"  Тому відношення повзе з {first.ratio:.1f}x до {last.ratio:.1f}x. Число «вдвічі")
    print("  швидше» без згадки про довжину репліки — це число без умов.")
    print()
    print("  Практичний висновок: якщо твої користувачі говорять короткими фразами, більшу")
    print("  частину виграшу дасть стрімінг генерації. Якщо довгими — стрімінгове")
    print("  розпізнавання, і воно ж дорожче в реалізації.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
