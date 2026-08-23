"""Розв'язок вправи 1: чому фільтр доступу мусить стояти ДО відбору top-k.

    python -m stages.s02_rag.solutions.exercise_1_filter_after_topk

Скрипт не міняє `store.py`. Він рахує обидва порядки поруч на тих самих даних — і показує
числами те, що словами звучить як педантизм.

Тут два спостереження, і друге виявилось важливішим за перше.

**Перше:** при неправильному порядку внутрішній документ усе одно **не витікає**. Перевірка
на витік лишається зеленою. Ламається дзеркальна властивість — дозволена відповідь тихо
зникає з видачі, і покупець отримує «не знайдено» на питання, на яке відповідь була.

**Друге:** чи побачиш ти цю ваду взагалі — залежить від `top_k`. При `top_k=3` правильна
відповідь ще влазить у трійку разом із двома внутрішніми, і обидва порядки дають однаковий
результат. При `top_k=2` внутрішні займають обидва слоти, і видача стає порожньою. Код
зламаний однаково в обох випадках; змінюється лише те, чи це видно.

Це і є причина, чому перевірка на цю властивість зашила `top_k=2` жорстко. Параметр, який
не має жодного стосунку до контролю доступу, вирішує, спрацює перевірка чи промовчить.
"""

from __future__ import annotations

from shared.embeddings import cosine, get_embedder
from stages.s02_rag.documents import INTERNAL, PUBLIC, load_documents
from stages.s02_rag.store import KnowledgeBase

QUESTION = "яка сума автоматичного повернення"
THRESHOLD = 0.2


def _scored(base: KnowledgeBase) -> list[tuple[float, str, str]]:
    """Усі фрагменти з оцінками й рівнем доступу, від найближчого до найдальшого."""
    scores = cosine(base.embedder.embed([QUESTION])[0], base.vectors)
    rows = [
        (float(scores[i]), base.fragments[i].label, base.access[i])
        for i in range(len(base.fragments))
    ]
    return sorted(rows, key=lambda row: row[0], reverse=True)


def _labels(rows: list[tuple[float, str, str]]) -> list[str]:
    return [label for score, label, _ in rows if score >= THRESHOLD]


def _show(title: str, rows: list[tuple[float, str, str]]) -> None:
    print(f"    {title}")
    visible = [row for row in rows if row[0] >= THRESHOLD]
    if not visible:
        print("        (порожньо — покупець побачить «нічого не знайдено»)")
        return
    for score, label, access in visible:
        print(f"        {score:.3f}  {label:<34} [{access}]")


def main() -> int:
    base = KnowledgeBase(embedder=get_embedder(), threshold=THRESHOLD)
    base.index(load_documents(), size=40, overlap=10)
    ranked = _scored(base)

    print(f"Питання покупця: «{QUESTION}»")
    print(f"Рівень доступу питальника: {PUBLIC}, поріг: {THRESHOLD}\n")
    print("Повний порядок за близькістю, без будь-якого фільтра:")
    for score, label, access in ranked[:5]:
        print(f"    {score:.3f}  {label:<34} [{access}]")
    print(
        f"\nДва найближчі фрагменти — {INTERNAL}. Це не випадковість: документ навмисно\n"
        "містить ті самі слова, що й питання покупця. Саме тому він придатний як пастка.\n"
    )

    for top_k in (3, 2):
        print("=" * 78)
        print(f"top_k = {top_k}")

        right = [row for row in ranked if row[2] == PUBLIC][:top_k]
        _show("ПРАВИЛЬНО (фільтр ДО відбору) — покупець бачить:", right)

        head = ranked[:top_k]
        wrong = [row for row in head if row[2] == PUBLIC]
        _show("НЕПРАВИЛЬНО (фільтр ПІСЛЯ відбору) — покупець бачить:", wrong)

        stolen = [label for _, label, access in head if access != PUBLIC]
        lost = sorted(set(_labels(right)) - set(_labels(wrong)))
        print("\n    внутрішніх витекло:            0 — в обох порядках")
        print(f"    внутрішні зайняли слотів:      {len(stolen)}")
        print(f"    загублено дозволеного:         {lost or 'нічого'}")
        print(f"    вада видима:                   {'ТАК' if lost else 'ні — але вона є'}\n")

    print("=" * 78)
    print(
        """
Витоку немає в жодному з варіантів — тому тест на витік мовчить скрізь.

Ламається дзеркальна властивість: дозволене мусить дійти. Тест на «погане не сталося»
ніколи не замінить тесту на «хороше сталося» — це різні твердження, і покриття одного
створює хибне відчуття, що покрито обидва.

І окремо: та сама вада при top_k=3 не проявляється взагалі. Якби перевірку писали «як
у продакшні», з top_k=3, вона була б зеленою на зламаному коді. Перевірка, зав'язана на
конкретне значення параметра, виглядає крихкою рівно доти, доки не з'ясується, що саме
це значення й робить властивість спостережною.
""".strip()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
