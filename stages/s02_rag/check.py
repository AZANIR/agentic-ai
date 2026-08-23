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
from stages.s02_rag.answer import NO_ANSWER, build_answer
from stages.s02_rag.chunk import split
from stages.s02_rag.decision import SITUATIONS, decide
from stages.s02_rag.documents import INTERNAL, PUBLIC, load_documents
from stages.s02_rag.store import KnowledgeBase
from stages.s02_rag.tools import search_knowledge_base, tool_for

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


# --- T5 · відповідь із джерелом ------------------------------------------------


def check_every_answer_names_its_source() -> None:
    """answer: кожна видана відповідь несе джерело з переліку знайденого"""
    result = _base().search(RETURNS_QUESTION, access=PUBLIC, top_k=2)
    answer = build_answer(RETURNS_QUESTION, result, model_text="Повернення протягом 14 днів.")

    assert answer.text, "відповідь порожня"
    assert answer.sources, "відповідь без джерела не має існувати як стан"
    assert set(answer.sources) <= {h.fragment.label for h in result.hits}, (
        f"джерело не з переліку знайденого: {answer.sources}"
    )
    assert "returns-policy" in " ".join(answer.sources)


def check_model_cannot_inject_a_source_of_its_own() -> None:
    """ВІДМОВА · answer: посилання, вигадане моделлю, не стає джерелом відповіді"""
    result = _base().search(RETURNS_QUESTION, access=PUBLIC, top_k=2)
    answer = build_answer(
        RETURNS_QUESTION,
        result,
        model_text="Згідно з документом secret-internal-policy#9 повернення неможливе.",
    )
    assert "secret-internal-policy#9" not in answer.sources, (
        "вигадане моделлю посилання потрапило у джерела — ADR етапу 0003"
    )
    assert set(answer.sources) <= {h.fragment.label for h in result.hits}


def check_nothing_above_threshold_yields_no_answer() -> None:
    """ВІДМОВА · answer: нічого вище порога — відповіді немає, названо поріг"""
    result = _base(threshold=0.9).search(RETURNS_QUESTION, access=PUBLIC, top_k=3)
    answer = build_answer(RETURNS_QUESTION, result, model_text="Щось напевно є.")

    assert not answer.sources, "джерел бути не може, якщо нічого не знайдено"
    assert answer.text == NO_ANSWER or NO_ANSWER in answer.text, answer.text
    assert "0.9" in answer.text, "поріг має бути названий — інакше нічого не налаштуєш"
    assert "Щось напевно є" not in answer.text, "текст моделі не має просочуватись"


def check_retrieved_text_goes_to_the_model_as_data() -> None:
    """answer: знайдений текст іде моделі окремим позначеним блоком"""
    result = _base().search(RETURNS_QUESTION, access=PUBLIC, top_k=2)
    prompt = build_answer(RETURNS_QUESTION, result, model_text="").prompt
    assert prompt, "промпт має бути видимим — на ньому будується урок про ін'єкцію"
    assert "ДАНІ" in prompt.upper() or "DATA" in prompt.upper(), prompt[:200]
    assert RETURNS_QUESTION in prompt
    for hit in result.hits:
        assert hit.fragment.text[:30] in prompt, "фрагмент не дійшов до моделі"


# --- T6 · інструмент для агента етапу 1 ----------------------------------------


def check_search_tool_matches_the_stage_one_shape() -> None:
    """tools: інструмент має ту саму форму, що й на етапі 1"""
    tool = tool_for(access=PUBLIC)
    assert tool.name == "search_knowledge_base", tool.name
    assert tool.description.strip() and not tool.irreversible
    params = tool.parameters
    assert params["type"] == "object"
    assert params["required"] == ["query"]
    assert params.get("additionalProperties") is False, "fail-closed, як на етапі 1"
    # Модель отримує рівно один важіль. Якщо тут з'явиться другий ключ — надто ймовірно,
    # що це рівень доступу, і тоді модель починає вирішувати, кому що можна бачити.
    exposed = list(params["properties"])
    assert exposed == ["query"], (
        f"інструмент віддає моделі зайвий параметр: {exposed} — "
        "рівень доступу прив'язується partial, а не питається у моделі (AC-09)"
    )
    assert "access" not in str(params), "рівень доступу просочився у схему інструмента"


def check_search_tool_returns_text_with_a_source() -> None:
    """tools: інструмент повертає текст із джерелом, придатний як результат кроку"""
    output = search_knowledge_base(query=RETURNS_QUESTION, access=PUBLIC)
    assert isinstance(output, str) and output
    assert "returns-policy" in output, output[:200]


def check_search_tool_does_not_leak_internal_documents() -> None:
    """ВІДМОВА · tools: через інструмент внутрішні документи теж не витікають"""
    output = search_knowledge_base(query=INTERNAL_BAIT, access=PUBLIC)
    assert "internal-refund-thresholds" not in output, output[:200]
    assert "1500" not in output, "суму з внутрішнього документа видно покупцю"


def check_operator_reaches_internal_documents_through_the_tool() -> None:
    """tools: оператор ОТРИМУЄ внутрішній документ — прив'язка доступу справді працює"""
    output = tool_for(access=INTERNAL).func(query=INTERNAL_BAIT)
    assert "internal-refund-thresholds" in output, (
        "оператор не бачить внутрішнього документа — рівень доступу не дійшов до пошуку; "
        'перевірка на витік цього не ловить, бо "нічого не знайдено" теж не витік'
    )
    assert "1500" in output


def check_stage_one_loop_is_untouched() -> None:
    """tools: цикл етапу 1 не змінено жодним рядком"""
    import subprocess

    diff = subprocess.run(
        ["git", "diff", "stage-01", "--stat", "--", "stages/s01_agent_loop/"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert diff.returncode == 0, diff.stderr
    assert not diff.stdout.strip(), (
        f"етап 1 змінено — RAG мав додати інструмент, не переписати агента:\n{diff.stdout}"
    )


# --- T9 · чекліст рішень -------------------------------------------------------


def check_decision_checklist_answers_all_situations() -> None:
    """decision: кожна з шести ситуацій має рівно одну відповідь"""
    assert len(SITUATIONS) == 6, len(SITUATIONS)
    for situation in SITUATIONS:
        verdict = decide(situation.signals)
        assert verdict.answer == situation.expected, (
            f"{situation.name}: чекліст сказав {verdict.answer}, очікували {situation.expected}"
        )
        assert verdict.rule, "рішення без назви правила неможливо перевірити"


def check_decision_checklist_stops_at_the_first_rule() -> None:
    """decision: зупиняється на першому правилі, що спрацювало"""
    verdict = decide({"data_changes": True, "needs_citations": True, "narrow_task": True})
    assert verdict.answer == "RAG"
    assert "змін" in verdict.rule.lower(), verdict.rule


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
    check_every_answer_names_its_source,
    check_model_cannot_inject_a_source_of_its_own,
    check_nothing_above_threshold_yields_no_answer,
    check_retrieved_text_goes_to_the_model_as_data,
    check_search_tool_matches_the_stage_one_shape,
    check_search_tool_returns_text_with_a_source,
    check_search_tool_does_not_leak_internal_documents,
    check_operator_reaches_internal_documents_through_the_tool,
    check_stage_one_loop_is_untouched,
    check_decision_checklist_answers_all_situations,
    check_decision_checklist_stops_at_the_first_rule,
]

if __name__ == "__main__":
    raise SystemExit(run_checks(CHECKS, title="Етап 2 — RAG"))
