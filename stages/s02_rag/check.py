"""Перевірки етапу 2. Офлайн, без API-ключа, детерміновано.

Запуск: ``python -m stages.s02_rag.check``

Шість перевірок позначені як режими відмови. Найважливіша з них — не та, що ловить витік
внутрішнього документа, а сусідня: **дозволений документ не зник із видачі**. Без неї фільтр,
поставлений після відбору top-k, проходить усе — внутрішнє справді не витікає, просто
правильна відповідь тихо перетворюється на «нічого не знайдено» (ADR етапу 0002).
"""

from __future__ import annotations

from shared.check_runner import run_checks
from shared.config import Settings
from shared.embeddings import get_embedder
from stages.s02_rag.chunk import split
from stages.s02_rag.store import PUBLIC, KnowledgeBase, load_documents

SMALL = 40
LARGE = 120

RETURNS_QUESTION = "скільки днів на повернення товару"
SYNONYM_QUESTION = "як оформити відмову від покупки"
INTERNAL_BAIT = "яка сума автоматичного повернення"


def _base(*, size: int = SMALL, threshold: float = 0.2) -> KnowledgeBase:
    base = KnowledgeBase(embedder=get_embedder(), threshold=threshold)
    base.index(load_documents(), size=size, overlap=10)
    return base


# --- T2 · нарізка -------------------------------------------------------------


def check_chunking_covers_the_whole_text() -> None:
    """chunk: фрагменти покривають увесь текст і несуть джерело"""
    text = " ".join(f"слово{i}" for i in range(100))
    fragments = split(text, source="doc", size=30, overlap=0)
    assert len(fragments) == 4, len(fragments)
    assert " ".join(f.text for f in fragments).split() == text.split(), "текст загубився"
    assert all(f.source == "doc" for f in fragments)
    assert [f.position for f in fragments] == [0, 1, 2, 3]
    assert fragments[0].label == "doc#0", fragments[0].label


def check_chunking_overlap_keeps_the_seam() -> None:
    """chunk: перекриття зберігає думку, що припала на стик"""
    text = " ".join(f"с{i}" for i in range(50))
    fragments = split(text, source="doc", size=20, overlap=5)
    first, second = fragments[0].text.split(), fragments[1].text.split()
    assert first[-5:] == second[:5], "перекриття не працює — стик загубиться"


def check_chunking_survives_degenerate_documents() -> None:
    """ВІДМОВА · chunk: порожній і надто короткий документи не кидають винятку"""
    assert split("", source="empty", size=40) == []
    assert split("   \n  ", source="blank", size=40) == []
    tiny = split("Гарантія рік.", source="tiny", size=40)
    assert len(tiny) == 1 and tiny[0].text == "Гарантія рік."


def check_chunking_rejects_impossible_overlap() -> None:
    """ВІДМОВА · chunk: перекриття не менше за розмір — це помилка програміста"""
    try:
        split("а б в", source="x", size=10, overlap=10)
    except ValueError as exc:
        assert "перекриття" in str(exc)
    else:
        raise AssertionError("перекриття >= розміру дало б нескінченний цикл")


# --- T3 · база знань ----------------------------------------------------------


def check_knowledge_base_has_the_shapes_the_checks_need() -> None:
    """kb: у базі є все, на чому тримаються перевірки нижче"""
    docs = {d.name: d for d in load_documents()}
    assert "returns-policy" in docs, "немає цілі AC-01"
    internal = {n for n, d in docs.items() if d.access != PUBLIC}
    assert len(internal) >= 2, f"внутрішніх документів замало: {internal}"
    assert "internal-refund-thresholds" in internal
    assert any(not d.body.strip() for d in docs.values()), "немає порожнього документа"


def check_internal_document_really_outranks_the_permitted_one() -> None:
    """kb: пастка AC-05 справді пастка — без фільтра внутрішній виграє"""
    base = KnowledgeBase(embedder=get_embedder(), threshold=0.0)
    base.index(load_documents(), size=SMALL, overlap=10)
    unfiltered = base.search(INTERNAL_BAIT, access=None, top_k=2)
    sources = {hit.fragment.source for hit in unfiltered.hits}
    assert sources == {"internal-refund-thresholds"}, (
        f"без фільтра мали виграти внутрішні, а виграли {sources}. "
        "Пастка перестала бути пасткою — AC-05 тепер перевіряє збіг обставин"
    )


# --- T4 · пошук ---------------------------------------------------------------


def check_literal_question_ranks_the_right_document_first() -> None:
    """store: питання словами документа дає його першим, з видимими оцінками"""
    result = _base().search(RETURNS_QUESTION, access=PUBLIC, top_k=3)
    assert result.hits, "нічого не знайшлося на дослівне питання"
    assert result.hits[0].fragment.source == "returns-policy", result.hits[0].fragment.label
    assert result.hits[0].score > 0.4, result.hits[0].score
    assert [h.score for h in result.hits] == sorted((h.score for h in result.hits), reverse=True), (
        "видача не відсортована"
    )


def check_synonym_question_fails_to_find_it() -> None:
    """МЕЖА · store: те саме питання синонімами не знаходить — за задумом ADR-0001"""
    literal = _base().search(RETURNS_QUESTION, access=PUBLIC, top_k=1)
    synonym = _base().search(SYNONYM_QUESTION, access=PUBLIC, top_k=1)

    assert literal.hits, "дослівне мало знайтись"
    assert not synonym.hits, "синонім не мав пройти поріг — межа хеш-ембеддера зникла"
    assert synonym.best_score < literal.best_score / 2, (
        f"розрив замалий: дослівне {literal.best_score:.3f} проти "
        f"синонімічного {synonym.best_score:.3f}"
    )


def check_below_threshold_yields_nothing() -> None:
    """ВІДМОВА · store: нічого вище порога — порожньо, з названим порогом"""
    result = _base(threshold=0.9).search(RETURNS_QUESTION, access=PUBLIC, top_k=3)
    assert not result.hits, "поріг 0.9 не мав пропустити нічого"
    assert result.below_threshold, "прогін має знати, що спрацював саме поріг"
    assert result.threshold == 0.9
    assert result.closest, "найближчі мають лишатись видимими — інакше нічого не налаштуєш"
    assert result.closest[0].score < 0.9


def check_internal_document_never_reaches_a_shopper() -> None:
    """ВІДМОВА · store: внутрішній документ не потрапляє у видачу покупцю"""
    result = _base(threshold=0.0).search(INTERNAL_BAIT, access=PUBLIC, top_k=3)
    sources = {hit.fragment.source for hit in result.hits}
    assert not any(s.startswith("internal") for s in sources), f"витік: {sources}"
    assert result.filtered_out > 0, "фільтр мав щось відсіяти — інакше перевірка порожня"


def check_permitted_document_is_not_displaced_by_a_filtered_one() -> None:
    """ВІДМОВА · store: дозволений документ не зник — фільтр стоїть ДО відбору"""
    # Найважливіша перевірка етапу. На цьому запиті два внутрішні фрагменти обходять
    # дозволений за близькістю. Якщо фільтрувати ПІСЛЯ відбору top-k=2, обидва слоти
    # займуть внутрішні, їх приберуть — і покупець отримає порожньо замість правильної
    # відповіді. Витоку не буде; відповідь зникне.
    result = _base(threshold=0.0).search(INTERNAL_BAIT, access=PUBLIC, top_k=2)
    assert result.hits, (
        "дозволений документ зник із видачі — фільтр застосовано ПІСЛЯ відбору top-k "
        "(ADR етапу 0002)"
    )
    assert result.hits[0].fragment.source == "returns-policy", result.hits[0].fragment.label


def check_broken_documents_do_not_break_the_index() -> None:
    """ВІДМОВА · store: порожній і надто короткий документи названі, база лишається робочою"""
    base = _base()
    assert "empty" in base.report.skipped, base.report.skipped
    assert base.report.indexed >= 5, base.report.indexed
    assert base.search(RETURNS_QUESTION, access=PUBLIC, top_k=1).hits, "решта бази має шукатись"


def check_search_is_deterministic() -> None:
    """store: три прогони того самого запиту дають ідентичний порядок"""
    runs = []
    for _ in range(3):
        result = _base().search(RETURNS_QUESTION, access=PUBLIC, top_k=3)
        runs.append([(h.fragment.label, round(h.score, 6)) for h in result.hits])
    assert runs[0] == runs[1] == runs[2], runs


def check_chunk_size_changes_what_is_retrieved() -> None:
    """store: різна нарізка дає різний склад або порядок видачі"""
    small = _base(size=SMALL).search(RETURNS_QUESTION, access=PUBLIC, top_k=3)
    large = _base(size=LARGE).search(RETURNS_QUESTION, access=PUBLIC, top_k=3)
    assert [h.fragment.label for h in small.hits] != [h.fragment.label for h in large.hits] or [
        round(h.score, 3) for h in small.hits
    ] != [round(h.score, 3) for h in large.hits], (
        "дві нарізки дали ідентичну видачу — вправа про чанкінг втратила б сенс"
    )


def check_configured_provider_is_used_and_named() -> None:
    """embeddings: налаштований провайдер обирається й називається"""
    configured = Settings.load(source={"EMBEDDINGS_PROVIDER": "hash"})
    assert "hash" in get_embedder(configured).name
    # Справжній провайдер офлайн не перевіряється — половина AC-06 закривається
    # ручним чеклістом в уроці, як і на етапі 1.


CHECKS = [
    check_chunking_covers_the_whole_text,
    check_chunking_overlap_keeps_the_seam,
    check_chunking_survives_degenerate_documents,
    check_chunking_rejects_impossible_overlap,
    check_knowledge_base_has_the_shapes_the_checks_need,
    check_internal_document_really_outranks_the_permitted_one,
    check_literal_question_ranks_the_right_document_first,
    check_synonym_question_fails_to_find_it,
    check_below_threshold_yields_nothing,
    check_internal_document_never_reaches_a_shopper,
    check_permitted_document_is_not_displaced_by_a_filtered_one,
    check_broken_documents_do_not_break_the_index,
    check_search_is_deterministic,
    check_chunk_size_changes_what_is_retrieved,
    check_configured_provider_is_used_and_named,
]

if __name__ == "__main__":
    raise SystemExit(run_checks(CHECKS, title="Етап 2 — RAG"))
