"""Єдиний вхід до LLM. Ніде більше в репозиторії не створюється клієнт напряму (ADR-0003).

Один OpenAI-сумісний клієнт покриває п'ять провайдерів, бо всі вони реалізують той самий
HTTP-інтерфейс — різниця лише в ``base_url``:

    Groq        https://api.groq.com/openai/v1
    OpenRouter  https://openrouter.ai/api/v1
    Ollama      http://localhost:11434/v1
    LM Studio   http://localhost:1234/v1
    OpenAI      https://api.openai.com/v1

Код етапу від цього не залежить — він завжди пише той самий виклик:

    from shared.config import settings
    from shared.llm import get_client

    client = get_client(demo_script=[...])
    response = client.chat.completions.create(
        model=settings.llm_model, messages=messages, tools=tools
    )

Відома прогалина: Anthropic НЕ є OpenAI-сумісним і сюди не підключається — для нього
потрібен окремий адаптер за цим самим інтерфейсом (ADR-0003, розділ Negative).
"""

from __future__ import annotations

from typing import Any

from shared.config import ConfigError, Settings
from shared.config import settings as default_settings
from shared.fake_llm import FakeLLM

_FAKE_MODEL = "fake"


def get_client(
    demo_script: list[dict[str, Any]] | None = None,
    *,
    settings: Settings | None = None,
) -> Any:
    """Повернути клієнт LLM: справжній, якщо налаштований, інакше — підробку зі сценарієм.

    :param demo_script: кроки для :class:`~shared.fake_llm.FakeLLM`. Обов'язкові, коли
        справжнього провайдера немає — інакше немає чого відповідати, і чесніше впасти
        з поясненням, ніж вигадати відповідь.
    :param settings: явні налаштування замість прочитаних з оточення. Потрібні перевіркам,
        щоб описати «а якби провайдер був налаштований» без підміни модульного синглтона —
        підміна атрибута модуля працює, але це магія, якої новачок на першому етапі не
        зрозуміє, а звичайний параметр зрозуміє одразу.

    Пріоритет саме такий (справжній клієнт витісняє сценарій), щоб той самий ``run.py``
    працював і без ключа (навчання), і з ключем (реальний прогін) без зміни коду.
    """
    settings = settings or default_settings
    if settings.has_real_llm:
        import openai

        return openai.OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=60.0,
            max_retries=2,
        )

    if demo_script is not None:
        return FakeLLM(script=demo_script)

    raise ConfigError(
        "LLM не налаштований і сценарій для підробки не переданий.\n"
        "Або заповни LLM_BASE_URL / LLM_API_KEY / LLM_MODEL у .env "
        "(див. .env.example — Groq має безкоштовний рівень),\n"
        "або виклич get_client(demo_script=[...]) із заготовленим сценарієм."
    )


def get_model(settings: Settings | None = None) -> str:
    """Ім'я моделі для ``chat.completions.create(model=...)``."""
    return (settings or default_settings).llm_model or _FAKE_MODEL


def is_fake(client: Any) -> bool:
    """Чи це підробка. Потрібно рівно для одного: чесного банера у демо."""
    return isinstance(client, FakeLLM)


def banner(client: Any, settings: Settings | None = None) -> str:
    """Рядок, який демо друкує першим, щоб читач не сплутав підробку зі справжнім прогоном."""
    if is_fake(client):
        return (
            "[FakeLLM] Відповіді розігруються за сценарієм — мережі немає. "
            "Щоб побачити справжню модель, заповни LLM_* у .env."
        )
    settings = settings or default_settings
    return f"[LLM] {settings.llm_base_url} · model={get_model(settings)}"
