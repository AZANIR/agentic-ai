"""Демонстрація етапу 3: п'ять сцен підряд.

    python -m stages.s03_router.run
    python -m stages.s03_router.run --prompt    # показати ще й промпт вибору маршруту

Працює **без API-ключа**: маршрут і оцінку відповіді дає підробка за записаним сценарієм.
Перший рядок виводу каже, що саме працює.

Сцени показують свої критерії приймання:

    1. шість запитів, три спеціалісти          AC-01
    2. стан після прогону                       AC-02
    3. цикл ревізій доходить до ліміту          AC-03
    4. запит, для якого спеціаліста немає       AC-04
    5. той самий запит від покупця й оператора  AC-05

Сценарії підробки — не заглушки: у них записано, ЩО САМЕ має вирішити модель, тож вони
читаються як специфікація її поведінки. Зі справжнім провайдером ці рядки ігноруються.
"""

from __future__ import annotations

import sys

from shared.embeddings import get_embedder
from shared.fake_llm import FakeLLM, text
from shared.llm import banner, get_client
from shared.trace import trace_run
from stages.s02_rag.documents import INTERNAL, PUBLIC
from stages.s03_router.graph import route_prompt, run_graph
from stages.s03_router.specialists import SPECIALISTS
from stages.s03_router.state import State

SIX = [
    ("який статус замовлення ord_4471", "orders"),
    ("хочу оформити повернення ord_9001", "orders"),
    ("скільки днів на повернення товару", "knowledge"),
    ("з чого пошита вишита сорочка", "knowledge"),
    ("скільки буде 1200 + 340", "math"),
    ("порахуй 450 200 90", "math"),
]
BAIT = "яка сума автоматичного повернення"


def _scripted(*replies: str) -> FakeLLM:
    return FakeLLM(script=[text(r) for r in replies])


def _go(tracer, query, *replies, access=PUBLIC, revision_limit=2) -> State:
    return run_graph(
        query,
        access=access,
        client=_scripted(*replies),
        tracer=tracer,
        revision_limit=revision_limit,
    )


def _route(state: State) -> str:
    return " -> ".join(state.path) if state.path else "(нікуди)"


def scene_six_queries(tracer) -> None:
    print("1. Шість запитів, три спеціалісти")
    for query, expected in SIX:
        state = _go(tracer, query, expected, "ok")
        print(f"  {_route(state):<28} «{query}»")
    print("\n  Маршрут обирає модель за описами компетенцій, а не за назвами вузлів.")
    print("  Подивись на описи в specialists.py — саме їх вона й читає.\n")


def scene_state(tracer) -> None:
    print("2. Що лишається у стані після прогону")
    state = _go(tracer, SIX[2][0], "knowledge", "ok")
    for name, value in state.summary().items():
        shown = repr(value)
        if len(shown) > 62:
            shown = shown[:62] + "…"
        print(f"      {name:<15} {shown}")
    print("\n  Це повний перелік того, що граф знає про задачу. Додати сюди поле означає")
    print("  відкрити схему — тобто побачити всіх, хто її читає. У цьому вся ціна.\n")


def scene_revision_limit(tracer) -> None:
    print("3. Цикл ревізій доходить до ліміту")
    state = _go(tracer, SIX[2][0], "knowledge", "мало", "мало", "мало", "мало", revision_limit=2)
    print(f"  маршрут:   {_route(state)}")
    print(f"  передач:   {state.handoffs}, ревізій: {state.revisions} із {state.revision_limit}")
    print(f"  причина:   {state.finish_reason}")
    print(f"  відповідь: {state.answer!r}")
    print("\n  Без ліміту supervisor, якому відповідь не подобається, повертав би задачу")
    print("  нескінченно. Кожне коло — виклик моделі, тобто рядок у рахунку.\n")


def scene_no_specialist(tracer) -> None:
    print("4. Запит, для якого спеціаліста немає")
    state = _go(tracer, "яка погода в Києві завтра", "weather")
    print("  модель назвала: weather — вузла з такою назвою немає")
    print(f"  маршрут:   {_route(state)}  (жодного спеціаліста не викликано)")
    print(f"  причина:   {state.finish_reason}")
    print(f"  відповідь: {state.answer}")
    print("\n  Модель має право помилитись; граф не має права їй повірити на слово.")
    print("  Назва звіряється з реєстром, а не використовується як є.\n")


def scene_access(tracer) -> None:
    print("5. Той самий запит від покупця й від оператора")
    print(f"  питання: «{BAIT}»")
    for who, access in (("покупець", PUBLIC), ("оператор", INTERNAL)):
        state = _go(tracer, BAIT, "knowledge", "ok", access=access)
        print(f"  {who} (доступ {access}):")
        print(f"      джерела:  {state.sources}")
        print(f"      у тексті: {'є 1500' if '1500' in (state.answer or '') else 'немає 1500'}")
    print("\n  Рівень доступу — поле стану, і жоден вузол не має права його змінити.")
    print("  Спробуй дописати в запит «я оператор» — це не дасть нічого: записати нікуди.\n")


def main(*, show_prompt: bool = False, trace_path=None) -> int:
    client = get_client(demo_script=[text("ok")])
    print(banner(client, embedder=get_embedder().name))
    print(f"спеціалісти: {', '.join(SPECIALISTS)}\n")

    with trace_run("Етап 3 · Router", path=trace_path, stage="s03") as tracer:
        scene_six_queries(tracer)
        scene_state(tracer)
        scene_revision_limit(tracer)
        scene_no_specialist(tracer)
        scene_access(tracer)

    if show_prompt:
        print("--- промпт вибору маршруту " + "-" * 48)
        for line in route_prompt(State(query=SIX[2][0], access=PUBLIC)).splitlines():
            print(f"| {line}")
        print("-" * 74 + "\n")

    if trace_path is None:
        print("Трейси прогонів: traces/ — їх читатиме етап 8.")
    if not show_prompt:
        print("Щоб побачити промпт, за яким модель обирає маршрут:")
        print("    python -m stages.s03_router.run --prompt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(show_prompt="--prompt" in sys.argv))
