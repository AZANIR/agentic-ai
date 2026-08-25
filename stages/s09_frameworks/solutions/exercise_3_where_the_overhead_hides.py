"""Що саме бачить лічильник, коли його пересунути всередину реалізації.

    python -m stages.s09_frameworks.solutions.exercise_3_where_the_overhead_hides

Червона перевірка вправи 3 каже «надбавка на суто контрактному запиті». Вона не показує
**чому це важливо** — а важливо тут те, що зламаний лічильник виглядає точно як цілий.

Три позиції спостерігача на тому самому прогоні:

    МЕЖА ПРОВАЙДЕРА   бачить фактичний запит, яким би шаром він не був складений
    ВСЕРЕДИНІ         бачить те, що попросила реалізація, — тобто надбавки не бачить
    ЗВІТ ФРЕЙМВОРКА   бачить те, що фреймворк вирішив розповісти

Різниця між ними — не точність, а **напрямок помилки**. Усі три позиції дають число; дві з них
дають число, менше за правду, і жодна не дає підстав запідозрити це з таблиці.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.fake_llm import FakeLLM
from stages.s09_frameworks import baseline, contract
from stages.s09_frameworks.counters import Tally, counted, tokens

# Текст, який «фреймворк» додає від себе на кожному запиті: системна підказка, опис ролі,
# нагадування про формат. Написаний тут, щоб число було відоме наперед.
SCAFFOLDING = (
    "Ти дуже старанний агент підтримки. Дій крок за кроком, не поспішай, "
    "перевіряй себе й відповідай ввічливо. Формат відповіді: один абзац."
)


@dataclass
class Seen:
    """Що нарахував спостерігач із певної позиції."""

    where: str
    asked: int
    sent: int

    @property
    def overhead(self) -> int:
        return max(0, self.sent - self.asked)


def _padded_client() -> object:
    """Клієнт, що додає риштування до кожного запиту, — як це робить фреймворк ролей."""
    inner = FakeLLM(script=contract.script(), repeat_last=True)
    counting = counted(inner, contract.owned_texts())
    original = counting.chat.completions.create

    def padded(**kwargs: object) -> object:
        messages = [{"role": "system", "content": SCAFFOLDING}, *kwargs.get("messages", [])]
        return original(**{**kwargs, "messages": messages})

    counting.chat.completions.create = padded  # type: ignore[method-assign]
    return counting


def at_the_boundary() -> Seen:
    """Позиція 1: обгортка навколо клієнта. Бачить усе, що поїхало."""
    client = _padded_client()
    baseline.run(client)
    tally = client.tally  # type: ignore[attr-defined]
    return Seen("на межі провайдера", tally.asked, tally.sent)


def from_inside() -> Seen:
    """Позиція 2: лічильник усередині реалізації. Бачить лише те, що склала вона сама."""
    inner_tally = Tally(owned=contract.owned_texts())
    for text in (contract.RESEARCH_PROMPT, contract.WRITER_PROMPT.format(note=contract.NOTE)):
        inner_tally.observe({"messages": [{"role": "user", "content": text}]})
    inner_tally.observe({"tools": [contract.TOOL_SCHEMA]})
    return Seen("усередині реалізації", inner_tally.asked, inner_tally.sent)


def from_the_framework() -> Seen:
    """Позиція 3: звіт фреймворка. Тут — найдоброзичливіший варіант: він рахує чесно, але себе.

    Реальні фреймворки рапортують у різних одиницях, а дехто не рапортує взагалі. Навіть
    найкращий випадок дає число, яке не можна покласти поруч із числом сусіда.
    """
    client = _padded_client()
    baseline.run(client)
    tally = client.tally  # type: ignore[attr-defined]
    # Фреймворк вважає СВОЇ риштування частиною запиту: з його погляду він нічого не додав.
    return Seen("звіт фреймворка", tally.sent, tally.sent)


def main() -> int:
    truth = at_the_boundary()
    positions = [truth, from_inside(), from_the_framework()]

    print("Той самий прогін. Змінюється лише те, ЗВІДКИ дивиться лічильник.")
    print()
    print(f"   {'позиція':<22} {'просив':>8} {'пішло':>8} {'надбавка':>10}")
    for seen in positions:
        print(f"   {seen.where:<22} {seen.asked:>8} {seen.sent:>8} {seen.overhead:>10}")
    print()

    per_call = tokens(SCAFFOLDING)
    calls = truth.overhead // per_call
    print(f"   Риштування коштують {per_call} токенів НА КОЖНОМУ запиті, а запитів було")
    print(f"   {calls} — отже {truth.overhead}. Саме стільки бачить позиція «{truth.where}».")
    print()
    print("   Надбавка масштабується з кількістю кроків: довша задача платить більше разів")
    print("   за той самий текст. Одноразове число тут ввело б в оману рівно на цю різницю.")
    print()
    for seen in positions[1:]:
        lost = truth.overhead - seen.overhead
        print(f"   «{seen.where}» недорахувала {lost} — це {lost / truth.overhead:.0%} надбавки.")
    print()
    print("   Помилка не випадкова: обидві хибні позиції дають число МЕНШЕ за правду.")
    print("   Лічильник, що недорахував, показує фреймворк дешевшим — тобто помиляється")
    print("   у той самий бік, у який хочеться дивитись.")
    print()
    print("   І помітити це з таблиці неможливо: нуль у базової лінії правильний, а нуль")
    print("   у фреймворка виглядає як хороша новина. Саме тому перевірка доводить прилад")
    print("   НА ОБОХ КРАЯХ — контрактний запит дає нуль, чужий текст дає його розмір.")

    # Надбавка = розмір риштувань × кількість запитів. Одноразовий розмір тут був би
    # неправильним числом — і саме цей ассерт спіймав його в першій редакції прози.
    assert truth.overhead == tokens(SCAFFOLDING) * 2, (truth.overhead, tokens(SCAFFOLDING))
    assert from_inside().overhead == 0, "лічильник усередині раптом побачив надбавку"
    assert from_the_framework().overhead == 0, "звіт фреймворка раптом визнав власні риштування"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
