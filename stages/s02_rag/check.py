"""Перевірки етапу 2. Офлайн, без API-ключа, детерміновано.

Запуск: ``python -m stages.s02_rag.check``

Майже половина перевірок — режими відмови. Найважливіша з них — не та, що ловить витік
внутрішнього документа, а сусідня: **дозволений документ не зник із видачі**. Без неї фільтр,
поставлений після відбору top-k, проходить усе — внутрішнє справді не витікає, просто
правильна відповідь тихо перетворюється на «нічого не знайдено» (ADR етапу 0002).
"""

from __future__ import annotations

import io
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from shared.check_runner import require_tag, run_checks
from shared.config import ConfigError, Settings
from shared.embeddings import get_embedder
from shared.fake_llm import FakeLLM, text, tool_call
from shared.trace import iter_steps, trace_run
from stages.s01_agent_loop.loop import run_agent
from stages.s02_rag.answer import CLOSE_DATA, NO_ANSWER, OPEN_DATA, build_answer
from stages.s02_rag.chunk import split
from stages.s02_rag.decision import FINE_TUNING, PROMPT, RAG, RULES, SITUATIONS, decide
from stages.s02_rag.documents import INTERNAL, NO_FILTER, PUBLIC, load_documents
from stages.s02_rag.run import main as demo_main
from stages.s02_rag.store import KnowledgeBase, SearchResult
from stages.s02_rag.tools import (
    describe,
    registry_with_search,
    search_knowledge_base,
    sources_from_transcript,
    tool_for,
)

SMALL = 40
LARGE = 120

RETURNS_QUESTION = "скільки днів на повернення товару"
SYNONYM_QUESTION = "як оформити відмову від покупки"
INTERNAL_BAIT = "яка сума автоматичного повернення"


def _base(*, size: int = SMALL, threshold: float = 0.2) -> KnowledgeBase:
    base = KnowledgeBase(embedder=get_embedder(), threshold=threshold)
    base.index(load_documents(), size=size, overlap=10)
    return base


# --- documents · рівень доступу -----------------------------------------------

_BROKEN = {
    "no-closing-fence": "---\ntitle: Секрет\naccess: internal\nВнутрішній секрет.\n",
    "byte-order-mark": "\ufeff---\ntitle: Секрет\naccess: internal\n---\nВнутрішній секрет.\n",
    "typo-in-key": "---\ntitle: Секрет\nacces: internal\n---\nВнутрішній секрет.\n",
    "indented-key": "---\ntitle: Секрет\n access: internal\n---\nВнутрішній секрет.\n",
    "wrong-case": "---\ntitle: Секрет\nAccess: Internal\n---\nВнутрішній секрет.\n",
    "no-frontmatter": "Внутрішній секрет без жодних метаданих.\n",
}


def check_broken_frontmatter_does_not_make_a_document_public() -> None:
    """ВІДМОВА · documents: зіпсовані метадані не роблять документ публічним"""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        for name, raw in _BROKEN.items():
            (directory / f"{name}.md").write_text(raw, encoding="utf-8")
        loaded = {d.name: d.access for d in load_documents(directory)}

    assert len(loaded) == len(_BROKEN), loaded
    public = sorted(name for name, access in loaded.items() if access == PUBLIC)
    assert not public, (
        f"зіпсовані метадані зробили документ публічним: {public} — дефолт має бути "
        "закритим, як у валідаторі етапу 1"
    )
    assert loaded["byte-order-mark"] == INTERNAL, "BOM з'їв відкривальну лінію frontmatter"
    assert loaded["wrong-case"] == INTERNAL, "ключ в іншому регістрі не розпізнано"


def check_unknown_access_value_is_not_trusted() -> None:
    """ВІДМОВА · documents: невідоме значення access не пропускається як є"""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        (directory / "typo-value.md").write_text(
            "---\ntitle: Секрет\naccess: pubic\n---\nВнутрішній секрет.\n", encoding="utf-8"
        )
        (directory / "empty-value.md").write_text(
            "---\ntitle: Секрет\naccess:\n---\nВнутрішній секрет.\n", encoding="utf-8"
        )
        loaded = {d.name: d.access for d in load_documents(directory)}

    assert loaded == {"typo-value": INTERNAL, "empty-value": INTERNAL}, (
        f"невідоме значення рівня доступу не звелося до закритого: {loaded}"
    )


def check_good_documents_still_load_with_their_declared_access() -> None:
    """documents: справна база читається, рівні доступу ті, що написані"""
    loaded = {d.name: d.access for d in load_documents()}
    assert loaded["returns-policy"] == PUBLIC, loaded
    assert loaded["internal-refund-thresholds"] == INTERNAL, loaded
    assert sum(1 for a in loaded.values() if a == INTERNAL) == 2, loaded
    assert all(d.title for d in load_documents()), "документ без заголовка"


# --- крайові випадки, знайдені рев'ю ------------------------------------------


def check_unknown_asker_cannot_become_full_access() -> None:
    """ВІДМОВА · store: None як рівень доступу — помилка, а не «показати все»"""
    base = _base()
    try:
        base.search(INTERNAL_BAIT, access=None, top_k=3)
    except (ValueError, TypeError) as error:
        assert "access" in str(error).lower() or "доступ" in str(error).lower(), error
    else:
        raise AssertionError(
            "None пройшов як «без фільтра» — а саме це значення дасть будь-яка "
            "нерозв'язана резолюція «хто питає»"
        )


def check_full_access_is_an_explicit_named_choice() -> None:
    """store: «без фільтра» лишається можливим, але лише названим сентинелом"""
    result = _base().search(INTERNAL_BAIT, access=NO_FILTER, top_k=3)
    assert any("internal" in hit.fragment.source for hit in result.hits), (
        "названий сентинел має давати повну видачу — інакше демо межі неможливе"
    )
    assert result.filtered_out == 0


def check_reindexing_does_not_duplicate_the_base() -> None:
    """ВІДМОВА · store: повторна індексація не подвоює базу"""
    base = _base()
    first = len(base.fragments)
    report = base.index(load_documents(), size=SMALL, overlap=10)

    assert len(base.fragments) == first, (
        f"після повторної індексації фрагментів {len(base.fragments)} замість {first} — "
        "дублікат з'їдає слот у top-k"
    )
    assert report.fragments == len(base.fragments), "звіт розійшовся з тим, що в індексі"
    labels = [hit.fragment.label for hit in base.search(RETURNS_QUESTION, access=PUBLIC).hits]
    assert len(labels) == len(set(labels)), f"дублікати у видачі: {labels}"


def check_negative_overlap_is_rejected_not_silently_dropped() -> None:
    """ВІДМОВА · chunk: від'ємне перекриття — помилка, а не мовчазна втрата тексту"""
    try:
        split("а б в г д", source="doc", size=2, overlap=-3)
    except ValueError as error:
        assert "перекриття" in str(error), error
    else:
        raise AssertionError("від'ємне перекриття викинуло слова з індексу мовчки")


def check_negative_top_k_is_rejected() -> None:
    """ВІДМОВА · store: від'ємний top_k — помилка, а не «майже все»"""
    try:
        _base().search(RETURNS_QUESTION, access=PUBLIC, top_k=-1)
    except ValueError as error:
        assert "top_k" in str(error), error
    else:
        raise AssertionError("від'ємний top_k віддав видачу замість того, щоб впасти")


def check_answer_survives_a_model_that_returned_nothing() -> None:
    """ВІДМОВА · answer: порожня відповідь моделі не валить прогін"""
    result = _base().search(RETURNS_QUESTION, access=PUBLIC, top_k=2)
    answer = build_answer(RETURNS_QUESTION, result, model_text=None)
    assert answer.text == "", answer.text
    assert answer.sources, "джерела не залежать від того, що сказала модель"


def check_no_answer_text_is_a_readable_sentence() -> None:
    """answer: відмова читається як речення й у випадку, коли не було чого розглядати"""
    empty = SearchResult(hits=[], closest=[], threshold=0.2)
    text = build_answer("будь-що", empty, model_text="").text
    assert ".," not in text and "., " not in text, f"зіпсоване речення: {text}"
    assert "поріг" in text.lower(), text


def check_tool_does_not_report_a_similarity_it_never_measured() -> None:
    """ВІДМОВА · tools: «найближче 0.00» не видається за виміряну близькість"""
    with tempfile.TemporaryDirectory() as tmp:
        base = KnowledgeBase(embedder=get_embedder(), threshold=0.2)
        base.index(load_documents(Path(tmp)), size=SMALL)
        assert not base.fragments
    text = describe(base.search(RETURNS_QUESTION, access=PUBLIC, top_k=3))
    assert "0.00" not in text, f"вигадана оцінка у відповіді інструмента: {text}"
    assert NO_ANSWER in text


# --- перевірки, що стверджують ВЛАСТИВІСТЬ, а не збіг ---------------------------


def check_retrieved_text_is_fenced_off_from_the_instructions() -> None:
    """ВІДМОВА · answer: огорожа блоку ДАНІ існує, а не просто слово «ДАНІ» у промпті"""
    result = _base().search(RETURNS_QUESTION, access=PUBLIC, top_k=2)
    prompt = build_answer(RETURNS_QUESTION, result, model_text="").prompt

    assert OPEN_DATA in prompt and CLOSE_DATA in prompt, (
        "маркерів блоку немає — знайдений текст приклеєний до інструкцій, і моделі нічим "
        "відрізнити чужі слова від твоїх"
    )
    head, block = prompt.split(OPEN_DATA, 1)
    block = block.split(CLOSE_DATA, 1)[0]
    for hit in result.hits:
        assert hit.fragment.text in block, (
            f"фрагмент {hit.fragment.label} лежить поза огорожею — сама огорожа декоративна"
        )
        assert hit.fragment.text not in head, "фрагмент продубльовано в інструкції"
    assert "ЛИШЕ на текст" in head, "інструкції мають лишатись до блоку, а не всередині"


def check_provider_choice_actually_reads_the_configuration() -> None:
    """ВІДМОВА · embeddings: фабрика читає конфігурацію, а не повертає дефолт завжди"""
    configured = get_embedder(
        Settings.load(
            source={
                "EMBEDDINGS_PROVIDER": "openai",
                "EMBEDDINGS_MODEL": "text-embedding-3-small",
                "LLM_BASE_URL": "https://example.invalid/v1",
                "LLM_API_KEY": "sk_test_not_a_real_key",
                "LLM_MODEL": "test",
            }
        )
    )
    assert configured.name == "api:text-embedding-3-small", (
        f"фабрика віддала {configured.name!r} — вона ігнорує EMBEDDINGS_PROVIDER"
    )
    assert get_embedder(Settings.load(source={})).name == "hash-words"


def check_unusable_embedder_configuration_is_refused_at_startup() -> None:
    """ВІДМОВА · embeddings: непридатна конфігурація падає на старті, а не при першому запиті"""
    for source, expect in (
        ({"EMBEDDINGS_PROVIDER": "нісенітниця"}, "нісенітниця"),
        ({"EMBEDDINGS_PROVIDER": "openai"}, "LLM_BASE_URL"),
    ):
        try:
            get_embedder(Settings.load(source=source))
        except ConfigError as error:
            assert expect in str(error), f"текст помилки не називає причини: {error}"
        else:
            raise AssertionError(f"конфігурація {source} мала бути відхилена")


def check_overlap_does_not_produce_a_fragment_inside_another() -> None:
    """ВІДМОВА · chunk: перекриття не плодить фрагмент, цілком вкладений у попередній"""
    fragments = split(" ".join(f"с{i}" for i in range(50)), source="doc", size=20, overlap=10)
    assert len(fragments) == 4, [f.label for f in fragments]
    assert fragments[-1].text not in fragments[-2].text, (
        "останній фрагмент цілком лежить усередині попереднього — той самий текст "
        "індексується двічі й з'їдає слот у top-k"
    )
    for document in load_documents():
        pieces = split(document.body, source=document.name, size=SMALL, overlap=10)
        texts = [p.text for p in pieces]
        assert len(texts) == len(set(texts)), f"дублікати фрагментів у {document.name}"


def check_decision_checklist_keeps_the_six_situations_it_documents() -> None:
    """ВІДМОВА · decision: склад чекліста закріплено — заміна ситуацій не проходить тихо"""
    names = [s.name for s in SITUATIONS]
    assert len(names) == len(set(names)) == 7, f"склад чекліста змінився: {names}"

    signals = {key for s in SITUATIONS for key in s.signals}
    declared = {rule.signal for rule in RULES}
    assert signals <= declared, (
        f"ситуація вмикає сигнал, якого немає у правилах: {signals - declared}"
    )
    assert declared <= signals, f"правило не перевіряється жодною ситуацією: {declared - signals}"

    verdicts = {decide(s.signals).answer for s in SITUATIONS}
    assert verdicts == {RAG, FINE_TUNING, PROMPT}, (
        f"чекліст дає не всі три вердикти: {verdicts} — ADR етапу 0004"
    )


def check_every_rule_is_exercised_by_a_situation() -> None:
    """decision: кожне правило має ситуацію, яка його вмикає"""
    for rule in RULES:
        matched = [s for s in SITUATIONS if s.signals.get(rule.signal)]
        assert matched, f"правило {rule.signal!r} не перевіряє жодна ситуація"
        assert decide({rule.signal: True}).answer == rule.answer


def check_demo_runs_offline_and_shows_five_scenes() -> None:
    """e2e · демо проходить офлайн, показує п'ять сцен і пише трейс"""
    buffer = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with redirect_stdout(buffer):
            code = demo_main(trace_path=path)
        steps = list(iter_steps(path))
    output = buffer.getvalue()

    assert code == 0, code
    for number in range(1, 6):
        assert f"\n{number}. " in output, f"сцена {number} не надрукувалась"
    assert "ембеддер hash-words" in output, "джерела не названі одним рядком (рішення №8)"
    assert output.count("[FakeLLM]") == 1, "другий банер повернувся"
    assert "пропущено: empty" in output, "зіпсований документ не названо у виводі (AC-08b)"
    assert "0.503" in output and "0.190" in output, "оцінки не видно в консолі (AC-01)"

    kinds = {step["kind"] for step in steps}
    assert {"search", "chunking", "threshold", "answer", "access"} <= kinds, kinds
    access = [step for step in steps if step["kind"] == "access"]
    assert any(step["filtered_out"] > 0 for step in access), (
        "факт відсіювання не потрапив у трейс — тому, хто розбирає інцидент, слідів не лишилось"
    )


def check_agent_answer_carries_a_source_from_the_transcript() -> None:
    """e2e · відповідь агента несе джерело, витягнуте системою зі стенограми (AC-09)"""
    client = FakeLLM(
        script=[
            tool_call("search_knowledge_base", {"query": RETURNS_QUESTION}),
            text("Повернути товар можна протягом 14 днів. Джерело вигадаю сам: fake-doc#7"),
        ]
    )
    with tempfile.TemporaryDirectory() as tmp:
        with trace_run("check", path=Path(tmp) / "t.jsonl", stage="s02") as tracer:
            result = run_agent(
                RETURNS_QUESTION,
                client=client,
                tracer=tracer,
                tools=registry_with_search(access=PUBLIC),
            )
    sources = sources_from_transcript(result.transcript)
    assert sources, "агент відповів без жодного джерела"
    assert "fake-doc#7" not in sources, "вигадане моделлю посилання просочилось у джерела"
    assert any("returns-policy" in label for label in sources), sources


def check_lesson_numbers_match_the_suite() -> None:
    """ВІДМОВА · урок: числа в прозі збігаються з тим, що друкує команда"""
    total, failures = len(CHECKS), sum(1 for c in CHECKS if (c.__doc__ or "").startswith("ВІДМОВА"))
    here = Path(__file__).parent
    for name, sentence in (
        ("README.md", f"{total} перевірок, {failures} із них на режими відмови"),
        ("CHECKLIST.md", f"{total} зелених перевірок, {failures} із них на режими відмови"),
        ("README.en.md", f"{total} checks, {failures} of them on failure modes"),
    ):
        page = (here / name).read_text(encoding="utf-8")
        assert sentence in page, (
            f"{name} не містить рядка {sentence!r} — проза розійшлася з тим, що друкує "
            "команда, яку той самий урок наказує запустити"
        )


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
    unfiltered = base.search(INTERNAL_BAIT, access=NO_FILTER, top_k=2)
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
    """ВІДМОВА · store: порожній документ названо, база лишається робочою"""
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


def check_search_tool_says_not_found_instead_of_serving_noise() -> None:
    """ВІДМОВА · tools: питання не по темі дає чесне «не знайдено», а не найближчий шум"""
    output = search_knowledge_base(query="яка погода в Києві завтра", access=PUBLIC)
    assert NO_ANSWER in output, (
        f"інструмент віддав агенту найближчий шум замість відмови: {output[:120]}"
    )
    assert "поріг" in output, "агент має бачити, який поріг не перетнули"


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

    require_tag("stage-01")

    diff = subprocess.run(
        # Лише реалізація: файл перевірок виключено з тієї ж причини, що й на етапі 3 —
        # спільна інфраструктурна правка проходить крізь усі `check.py`.
        [
            "git",
            "diff",
            "stage-01",
            "--stat",
            "--",
            "stages/s01_agent_loop/*.py",
            ":(exclude)stages/s01_agent_loop/check.py",
        ],
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
    assert len(SITUATIONS) == 7, len(SITUATIONS)
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


# --- T8 · e2e -----------------------------------------------------------------


def check_stage_one_agent_picks_the_search_tool() -> None:
    """e2e · агент етапу 1 сам обирає пошук по базі й доводить відповідь до кінця"""
    client = FakeLLM(
        script=[
            tool_call("search_knowledge_base", {"query": RETURNS_QUESTION}),
            text("Повернути товар можна протягом 14 днів."),
        ]
    )
    with tempfile.TemporaryDirectory() as tmp:
        with trace_run("check", path=Path(tmp) / "t.jsonl", stage="s02") as tracer:
            result = run_agent(
                RETURNS_QUESTION,
                client=client,
                tracer=tracer,
                tools=registry_with_search(access=PUBLIC),
            )
    assert result.ok, f"агент не дійшов до відповіді: {result}"
    assert "14 днів" in (result.answer or "")
    observed = [s for s in result.transcript if s.get("role") == "tool"]
    assert observed, "інструмент не викликався — міст не працює"
    assert "returns-policy" in observed[0]["content"], observed[0]["content"][:120]


def check_checks_run_offline_and_cover_failure_modes() -> None:
    """e2e · увесь набір іде без мережі, і відмов серед перевірок не менше трьох"""
    assert not Settings.load(source={}).has_real_llm, (
        "з порожнім оточенням провайдера бути не може — інакше набір мовчки пішов би в мережу"
    )
    labels = [(c.__doc__ or "") for c in CHECKS]
    failures = [d for d in labels if d.startswith("ВІДМОВА")]
    assert len(failures) >= 3, f"режимів відмови лише {len(failures)} — етап учить не тому"
    assert all(labels), "перевірка без опису не читається у виводі"
    assert get_embedder().name == "hash-words", (
        "перевірки мають іти на детермінованому ембеддері, інакше числа попливуть"
    )


CHECKS = [
    check_retrieved_text_is_fenced_off_from_the_instructions,
    check_provider_choice_actually_reads_the_configuration,
    check_unusable_embedder_configuration_is_refused_at_startup,
    check_overlap_does_not_produce_a_fragment_inside_another,
    check_decision_checklist_keeps_the_six_situations_it_documents,
    check_every_rule_is_exercised_by_a_situation,
    check_demo_runs_offline_and_shows_five_scenes,
    check_agent_answer_carries_a_source_from_the_transcript,
    check_lesson_numbers_match_the_suite,
    check_unknown_asker_cannot_become_full_access,
    check_full_access_is_an_explicit_named_choice,
    check_reindexing_does_not_duplicate_the_base,
    check_negative_overlap_is_rejected_not_silently_dropped,
    check_negative_top_k_is_rejected,
    check_answer_survives_a_model_that_returned_nothing,
    check_no_answer_text_is_a_readable_sentence,
    check_tool_does_not_report_a_similarity_it_never_measured,
    check_broken_frontmatter_does_not_make_a_document_public,
    check_unknown_access_value_is_not_trusted,
    check_good_documents_still_load_with_their_declared_access,
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
    check_search_tool_says_not_found_instead_of_serving_noise,
    check_search_tool_does_not_leak_internal_documents,
    check_operator_reaches_internal_documents_through_the_tool,
    check_stage_one_loop_is_untouched,
    check_decision_checklist_answers_all_situations,
    check_decision_checklist_stops_at_the_first_rule,
    check_stage_one_agent_picks_the_search_tool,
    check_checks_run_offline_and_cover_failure_modes,
]

if __name__ == "__main__":
    raise SystemExit(run_checks(CHECKS, title="Етап 2 — RAG"))
