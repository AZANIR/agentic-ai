"""Демонстрація етапу 2: п'ять сцен підряд.

    python -m stages.s02_rag.run
    python -m stages.s02_rag.run --prompt    # показати ще й промпт, який іде моделі

Працює **без API-ключа**, як і етап 1: ембеддинги за замовчуванням рахуються локально, а
текст відповіді дає підробка за записаним сценарієм. Перший рядок виводу каже, що саме
працює зараз.

Кожна сцена показує свій критерій приймання:

    1. дослівне питання проти синонімів        AC-01, AC-03
    2. дві нарізки поруч                       AC-04
    3. нічого вище порога — відповіді немає     AC-02
    4. відповідь із джерелом, доданим системою  AC-02, AC-06
    5. те саме питання від покупця й оператора  AC-05

Жодна сцена не каже «правильно так». Числа показані, висновок робить читач — це і є
різниця між демонстрацією й рекламою.
"""

from __future__ import annotations

import sys

from shared.embeddings import get_embedder
from shared.fake_llm import text
from shared.llm import banner, get_client, get_model
from shared.trace import trace_run
from stages.s02_rag.answer import build_answer, build_prompt
from stages.s02_rag.documents import INTERNAL, PUBLIC, load_documents
from stages.s02_rag.store import KnowledgeBase, SearchResult

LITERAL = "скільки днів на повернення товару"
SYNONYM = "як оформити відмову від покупки"
BAIT = "яка сума автоматичного повернення"

SCRIPT = [text("Повернути товар можна протягом 14 днів з дня отримання замовлення.")]


def _base(*, size: int, threshold: float = 0.2, announce: bool = False) -> KnowledgeBase:
    base = KnowledgeBase(embedder=get_embedder(), threshold=threshold)
    report = base.index(load_documents(), size=size, overlap=10)
    if announce:
        print(f"  проіндексовано: {report.indexed} документів, {report.fragments} фрагментів")
        for name, reason in report.skipped.items():
            print(f"  пропущено: {name} — {reason}")
        print()
    return base


def _show(result: SearchResult, *, indent: str = "    ") -> None:
    """Показати видачу з числами. Без чисел це магія, з числами — інженерія."""
    pool = result.hits or result.closest
    if not pool:
        print(f"{indent}(порожньо)")
        return
    for hit in pool:
        mark = " " if hit.score >= result.threshold else "×"
        print(f"{indent}{mark} {hit.score:.3f}  {hit.fragment.label}")
    if result.below_threshold:
        print(f"{indent}  жодне не дотягло до порога {result.threshold}")


def scene_literal_vs_synonym(tracer) -> None:
    print("1. Те саме питання: словами документа й синонімами")
    base = _base(size=40, announce=True)
    for label, question in (("дослівно ", LITERAL), ("синонімами", SYNONYM)):
        result = base.search(question, access=PUBLIC, top_k=3)
        print(f"  {label}: «{question}»")
        _show(result)
        tracer.step("search", question=question, best=round(result.best_score, 3))
    print("\n  Це не поламаний пошук, а межа хешу за словами: спільних слів немає — немає")
    print("  й близькості. Справжні ембеддинги знімають саме цю межу (ADR етапу 0001).\n")


def scene_two_chunk_sizes(tracer) -> None:
    print("2. Дві нарізки поруч: 40 слів і 120 слів")
    for size in (40, 120):
        result = _base(size=size).search(LITERAL, access=PUBLIC, top_k=3)
        print(f"  фрагмент {size:>3} слів:")
        _show(result, indent="      ")
        tracer.step("chunking", size=size, best=round(result.best_score, 3))
    print("\n  Дрібніше — точніше влучання, але менше контексту навколо відповіді.")
    print("  Більше — навпаки. Правильного розміру немає, є придатний для твоїх питань.\n")


def scene_below_threshold(tracer) -> None:
    print("3. Поріг: коли чесніше не відповісти")
    result = _base(size=40, threshold=0.9).search(LITERAL, access=PUBLIC, top_k=3)
    _show(result, indent="  ")
    answer = build_answer(LITERAL, result, model_text="(модель навіть не викликалась)")
    print(f"  -> {answer.text}")
    print(f"  -> джерел: {len(answer.sources)}; відповідь обґрунтована: {answer.grounded}")
    tracer.step("threshold", threshold=0.9, grounded=answer.grounded)
    print("\n  Порожня видача — це стан, а не збій. Негрунтована відповідь тут не існує")
    print("  як стан узагалі: немає джерел — немає й тексту від моделі.\n")


def scene_grounded_answer(tracer, client, *, show_prompt: bool) -> None:
    print("4. Відповідь із джерелом, яке додала система")
    result = _base(size=40).search(LITERAL, access=PUBLIC, top_k=2)
    prompt = build_prompt(LITERAL, result.hits)
    reply = client.chat.completions.create(
        model=get_model(), messages=[{"role": "user", "content": prompt}]
    )
    answer = build_answer(LITERAL, result, model_text=reply.choices[0].message.content)
    print(f"  питання: «{LITERAL}»")
    print(f"  відповідь: {answer.text}")
    print(f"  джерела: {', '.join(answer.sources)}")
    tracer.step("answer", sources=answer.sources, grounded=answer.grounded)
    if show_prompt:
        print("\n  --- промпт, який пішов моделі " + "-" * 44)
        for line in prompt.splitlines():
            print(f"  | {line}")
        print("  " + "-" * 74)
    print("")
    print("  Друге джерело — про доставку, не про повернення: воно перетнуло поріг,")
    print("  тож формально це джерело. Ось межа етапу 2 на власні очі: джерело під")
    print("  відповіддю гарантовано ІСНУЄ, але не гарантує, що відповідь із нього")
    print("  випливає. Це вже вимірювання — етап 8.")
    print("")
    print("  Джерела взяті з переліку знайденого, а не з тексту моделі. Послатися на")
    print("  документ, якого не було у видачі, тут технічно нема звідки (ADR етапу 0003).\n")


def scene_access_levels(tracer) -> None:
    print("5. Те саме питання від покупця й від оператора")
    base = _base(size=40)
    print(f"  питання: «{BAIT}»")
    for who, access in (("покупець ", PUBLIC), ("оператор ", INTERNAL)):
        result = base.search(BAIT, access=access, top_k=3)
        print(f"  {who} (доступ {access}):")
        _show(result, indent="      ")
        tracer.step(
            "access",
            who=access,
            labels=[h.fragment.label for h in result.hits],
            filtered_out=result.filtered_out,
        )
    print("\n  Внутрішній документ виграв би за близькістю — і саме тому це перевірка")
    print("  фільтра, а не збіг обставин. Фільтр стоїть ДО відбору top-k, тому покупець")
    print("  бачить правильну публічну відповідь, а не «нічого не знайдено».\n")


def main(*, show_prompt: bool = False, trace_path=None) -> int:
    client = get_client(demo_script=SCRIPT)
    print(banner(client, embedder=get_embedder().name))
    print()

    with trace_run("Етап 2 · RAG", path=trace_path, stage="s02") as tracer:
        scene_literal_vs_synonym(tracer)
        scene_two_chunk_sizes(tracer)
        scene_below_threshold(tracer)
        scene_grounded_answer(tracer, client, show_prompt=show_prompt)
        scene_access_levels(tracer)

    if trace_path is None:
        print("Трейси прогонів: traces/ — їх читатиме етап 8.")
    if not show_prompt:
        print("Щоб побачити промпт, який іде моделі (там видно межу блоку ДАНІ):")
        print("    python -m stages.s02_rag.run --prompt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(show_prompt="--prompt" in sys.argv))
