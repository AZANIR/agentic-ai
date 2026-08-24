"""Перевірки ядра ``shared`` — фундамент, на якому стоять усі етапи.

Запуск: ``python -m shared.check``

Половина перевірок нижче — на режими відмови. Це не перестраховка: саме заради них
підробний LLM взагалі існує (ADR-0006). «Ліміт кроків спрацював» неможливо перевірити
на справжній моделі, бо вона недетермінована.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from shared.check_runner import run_checks
from shared.config import LOCAL, PROD, ConfigError, Settings
from shared.embeddings import get_embedder
from shared.fake_llm import FakeLLM, FakeLLMError, text, tool_call
from shared.llm import banner, get_client, is_fake
from shared.trace import group_by_trace, trace_run

# Стеля часу для `scripts/check_all.py` — проти розростання, не ціль швидкодії.
# Заміряно 0.6 с. Піднімати можна свідомо, разом із числом у NFR.
BUDGET_SECONDS = 30

# --- config ------------------------------------------------------------------


def check_config_defaults_to_local() -> None:
    """config: порожнє оточення дає профіль local без справжнього LLM"""
    settings = Settings.load(source={})
    assert settings.profile == LOCAL, settings.profile
    assert not settings.is_prod
    assert not settings.has_real_llm, "порожній ключ не має вважатися справжнім провайдером"
    assert settings.agent_max_steps == 8, settings.agent_max_steps


def check_config_reads_provider() -> None:
    """config: заповнені LLM_* вмикають справжнього провайдера"""
    settings = Settings.load(
        source={
            "LLM_BASE_URL": "https://api.groq.com/openai/v1",
            "LLM_API_KEY": "gsk_test",
            "LLM_MODEL": "llama-3.3-70b-versatile",
            "AGENT_MAX_STEPS": "3",
        }
    )
    assert settings.has_real_llm
    assert settings.agent_max_steps == 3


def check_config_rejects_unsafe_prod() -> None:
    """ВІДМОВА · config: prod без API_KEYS не стартує"""
    unsafe = {
        "APP_PROFILE": PROD,
        "LLM_BASE_URL": "https://api.groq.com/openai/v1",
        "LLM_API_KEY": "gsk_test",
        "DATABASE_URL": "postgresql://x/y",
        "REDIS_URL": "redis://localhost:6379/0",
        # API_KEYS свідомо відсутній
    }
    try:
        Settings.load(source=unsafe)
    except ConfigError as exc:
        assert "API_KEYS" in str(exc), str(exc)
    else:
        raise AssertionError("prod без API_KEYS мав впасти, а стартував")


def check_config_rejects_bad_profile() -> None:
    """ВІДМОВА · config: невідомий APP_PROFILE не мовчить"""
    try:
        Settings.load(source={"APP_PROFILE": "staging"})
    except ConfigError as exc:
        assert "staging" in str(exc)
    else:
        raise AssertionError("невідомий профіль мав впасти")


# --- fake_llm ----------------------------------------------------------------


def check_fake_llm_is_deterministic() -> None:
    """fake_llm: однаковий сценарій дає однаковий результат"""
    script = [tool_call("get_weather", {"city": "Kyiv"}), text("У Києві +28°C.")]
    outputs = []
    for _ in range(3):
        client = FakeLLM(script=list(script))
        first = client.chat.completions.create(model="fake", messages=[])
        second = client.chat.completions.create(model="fake", messages=[])
        outputs.append(
            (
                first.choices[0].message.tool_calls[0].function.arguments,
                second.choices[0].message.content,
            )
        )
    assert len(set(outputs)) == 1, f"недетермінований результат: {outputs}"


def check_fake_llm_matches_openai_shape() -> None:
    """fake_llm: arguments — РЯДОК JSON, як у справжнього SDK"""
    client = FakeLLM(script=[tool_call("get_order_status", {"order_id": "ord_42"})])
    message = client.chat.completions.create(model="fake", messages=[]).choices[0].message
    call = message.tool_calls[0]
    assert message.content is None
    assert isinstance(call.function.arguments, str), "має бути рядок, інакше json.loads зайвий"
    assert json.loads(call.function.arguments) == {"order_id": "ord_42"}
    assert call.id and call.type == "function"


def check_fake_llm_counts_tokens() -> None:
    """fake_llm: usage непорожній — бюджет і етап 8 мають що рахувати"""
    client = FakeLLM(script=[text("коротка відповідь")])
    usage = client.chat.completions.create(
        model="fake", messages=[{"role": "user", "content": "привіт"}]
    ).usage
    assert usage.prompt_tokens > 0 and usage.completion_tokens > 0
    assert usage.total_tokens == usage.prompt_tokens + usage.completion_tokens


def check_fake_llm_exhaustion_is_loud() -> None:
    """ВІДМОВА · fake_llm: короткий сценарій падає з поясненням, а не мовчки"""
    client = FakeLLM(script=[text("одна відповідь")])
    client.chat.completions.create(model="fake", messages=[])
    try:
        client.chat.completions.create(model="fake", messages=[])
    except FakeLLMError as exc:
        assert "сценарій вичерпано" in str(exc)
        assert "repeat_last" in str(exc), "повідомлення має підказувати вихід"
    else:
        raise AssertionError("вичерпаний сценарій мав впасти")


def check_fake_llm_can_loop_forever() -> None:
    """fake_llm: always_calling нескінченно просить інструмент (основа перевірки лімітів)"""
    client = FakeLLM.always_calling("search_web", {"q": "агенти"})
    for _ in range(20):
        message = client.chat.completions.create(model="fake", messages=[]).choices[0].message
        assert message.tool_calls[0].function.name == "search_web"
    assert client.call_count == 20


# --- llm shim ----------------------------------------------------------------


def check_llm_returns_fake_without_key() -> None:
    """llm: без ключа зі сценарієм повертається підробка"""
    client = get_client(demo_script=[text("привіт")])
    assert is_fake(client)
    assert "FakeLLM" in banner(client)


def check_llm_refuses_without_script() -> None:
    """ВІДМОВА · llm: без ключа і без сценарію — зрозуміла помилка, не вигадана відповідь"""
    try:
        get_client()
    except ConfigError as exc:
        assert "LLM_BASE_URL" in str(exc) and "demo_script" in str(exc)
    else:
        raise AssertionError("get_client() без провайдера і без сценарію мав впасти")


# --- embeddings ----------------------------------------------------------------


def check_embedder_is_deterministic() -> None:
    """embeddings: той самий текст дає той самий вектор між викликами"""
    a = get_embedder().embed(["політика повернення діє 14 днів"])
    b = get_embedder().embed(["політика повернення діє 14 днів"])
    assert a.shape == b.shape, (a.shape, b.shape)
    assert (a == b).all(), "недетермінований ембеддер — перевірки етапу 2 стануть мигтливими"


def check_embedder_normalises_vectors() -> None:
    """embeddings: вектори нормовані — косинус зводиться до скалярного добутку"""
    import numpy as np

    vectors = get_embedder().embed(["коротко", "значно довший текст із багатьма словами"])
    lengths = np.linalg.norm(vectors, axis=1)
    assert np.allclose(lengths, 1.0), lengths
    # довжина тексту не має впливати на норму — інакше довгі документи вигравали б завжди


def check_embedder_finds_literal_overlap_not_synonyms() -> None:
    """embeddings: хеш знаходить дослівний збіг і НЕ знаходить синоніми — межа за задумом"""
    import numpy as np

    embedder = get_embedder()
    doc = embedder.embed(["повернення товару протягом 14 днів"])[0]
    literal = embedder.embed(["скільки днів на повернення товару"])[0]
    synonym = embedder.embed(["як оформити відмову від покупки"])[0]

    assert float(np.dot(doc, literal)) > float(np.dot(doc, synonym)), "дослівне має бути ближчим"
    assert float(np.dot(doc, synonym)) < 0.1, "синонім не має знаходитись — це межа з ADR-0001"


def check_embedder_reports_its_name() -> None:
    """embeddings: ембеддер називає себе, інакше не видно, що працює"""
    embedder = get_embedder()
    assert embedder.name, "ембеддер без імені — у банері буде порожньо"
    assert "hash" in embedder.name.lower(), embedder.name


# --- trace -------------------------------------------------------------------


def check_trace_writes_and_reads_back() -> None:
    """trace: кроки пишуться в JSONL і читаються назад як траєкторія"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("демо", path=path, stage="s01") as tracer:
            tracer.step("llm_call", model="fake")
            tracer.step("tool_call", name="get_weather")
        traces = group_by_trace(path)
        assert len(traces) == 1
        steps = next(iter(traces.values()))
        kinds = [s["kind"] for s in steps]
        assert kinds == ["run_start", "llm_call", "tool_call", "run_end"], kinds
        assert all(s["stage"] == "s01" for s in steps), "meta має потрапити в кожен крок"
        assert [s["seq"] for s in steps] == [1, 2, 3, 4]


def check_trace_records_failures() -> None:
    """ВІДМОВА · trace: виняток усередині прогону лишає слід run_error"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        try:
            with trace_run("падіння", path=path) as tracer:
                tracer.step("tool_call", name="delete_everything")
                raise ValueError("щось пішло не так")
        except ValueError:
            pass
        kinds = [s["kind"] for s in next(iter(group_by_trace(path).values()))]
        assert kinds == ["run_start", "tool_call", "run_error"], kinds
        assert "run_end" not in kinds, "невдалий прогін не має вдавати успішний"


CHECKS = [
    check_config_defaults_to_local,
    check_config_reads_provider,
    check_config_rejects_unsafe_prod,
    check_config_rejects_bad_profile,
    check_fake_llm_is_deterministic,
    check_fake_llm_matches_openai_shape,
    check_fake_llm_counts_tokens,
    check_fake_llm_exhaustion_is_loud,
    check_fake_llm_can_loop_forever,
    check_llm_returns_fake_without_key,
    check_llm_refuses_without_script,
    check_embedder_is_deterministic,
    check_embedder_normalises_vectors,
    check_embedder_finds_literal_overlap_not_synonyms,
    check_embedder_reports_its_name,
    check_trace_writes_and_reads_back,
    check_trace_records_failures,
]

if __name__ == "__main__":
    raise SystemExit(run_checks(CHECKS, title="shared — ядро адаптерів"))
