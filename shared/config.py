"""Налаштування з оточення — єдине місце, де читається ``.env``.

Профіль (``APP_PROFILE``) керує тим, ЯКІ адаптери будуть створені, і більше нічим.
Правило з ADR-0002: ``if profile == ...`` живе у фабриках ``shared/``, а не в коді етапів.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent

LOCAL = "local"
PROD = "prod"


class ConfigError(RuntimeError):
    """Оточення налаштоване так, що сервіс не можна безпечно запустити."""


def _env(source: dict[str, str] | None, key: str, default: str = "") -> str:
    src = source if source is not None else os.environ
    return (src.get(key) or default).strip()


def _int(source: dict[str, str] | None, key: str, default: int) -> int:
    raw = _env(source, key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} має бути цілим числом, а не {raw!r}") from exc


def _float(source: dict[str, str] | None, key: str, default: float) -> float:
    raw = _env(source, key)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} має бути числом, а не {raw!r}") from exc


def _csv(source: dict[str, str] | None, key: str) -> list[str]:
    return [part.strip() for part in _env(source, key).split(",") if part.strip()]


@dataclass(frozen=True)
class Settings:
    profile: str = LOCAL

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    agent_max_steps: int = 8

    embeddings_provider: str = "hash"
    embeddings_model: str = ""

    trace_sink: str = "jsonl"
    trace_dir: Path = REPO_ROOT / "traces"
    langfuse_host: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    database_url: str = ""
    redis_url: str = ""

    api_keys: list[str] = field(default_factory=list)
    cors_origins: list[str] = field(default_factory=list)
    rate_limit_per_minute: int = 30
    budget_usd_per_session: float = 0.25
    budget_usd_per_day: float = 5.00
    # Явний дозвіл підробки у профілі prod. Потрібен рівно для одного: підняти
    # продакшн-збірку локально й перевірити СПРАВЖНІ адаптери — Postgres замість
    # файлу, Redis замість памʼяті процесу — не маючи платного ключа (ADR-0009).
    allow_fake_llm: bool = False
    max_message_chars: int = 4000
    max_audio_seconds: int = 30

    @property
    def is_prod(self) -> bool:
        return self.profile == PROD

    @property
    def has_real_llm(self) -> bool:
        """Чи налаштований справжній провайдер.

        Порожній ключ — не помилка: це штатний спосіб сказати «дай FakeLLM».
        Саме тому весь курс проходиться без платіжної картки (ADR-0003).
        """
        return bool(self.llm_base_url and self.llm_api_key)

    @classmethod
    def load(cls, source: dict[str, str] | None = None) -> Settings:
        profile = _env(source, "APP_PROFILE", LOCAL).lower()
        if profile not in (LOCAL, PROD):
            raise ConfigError(f"APP_PROFILE має бути {LOCAL!r} або {PROD!r}, а не {profile!r}")

        trace_dir_raw = _env(source, "TRACE_DIR", "traces")
        trace_dir = Path(trace_dir_raw)
        if not trace_dir.is_absolute():
            trace_dir = REPO_ROOT / trace_dir

        settings = cls(
            profile=profile,
            llm_base_url=_env(source, "LLM_BASE_URL"),
            llm_api_key=_env(source, "LLM_API_KEY"),
            llm_model=_env(source, "LLM_MODEL"),
            agent_max_steps=_int(source, "AGENT_MAX_STEPS", 8),
            embeddings_provider=_env(source, "EMBEDDINGS_PROVIDER", "hash").lower(),
            embeddings_model=_env(source, "EMBEDDINGS_MODEL"),
            allow_fake_llm=_env(source, "ALLOW_FAKE_LLM") == "1",
            trace_sink=_env(source, "TRACE_SINK", "jsonl").lower(),
            trace_dir=trace_dir,
            langfuse_host=_env(source, "LANGFUSE_HOST"),
            langfuse_public_key=_env(source, "LANGFUSE_PUBLIC_KEY"),
            langfuse_secret_key=_env(source, "LANGFUSE_SECRET_KEY"),
            database_url=_env(source, "DATABASE_URL"),
            redis_url=_env(source, "REDIS_URL"),
            api_keys=_csv(source, "API_KEYS"),
            cors_origins=_csv(source, "CORS_ORIGINS"),
            rate_limit_per_minute=_int(source, "RATE_LIMIT_PER_MINUTE", 30),
            budget_usd_per_session=_float(source, "BUDGET_USD_PER_SESSION", 0.25),
            budget_usd_per_day=_float(source, "BUDGET_USD_PER_DAY", 5.00),
            max_message_chars=_int(source, "MAX_MESSAGE_CHARS", 4000),
            max_audio_seconds=_int(source, "MAX_AUDIO_SECONDS", 30),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Відмовитись стартувати в небезпечній конфігурації.

        Це межа довіри, а не зручність: сервіс без автентифікації, який ходить до
        платного LLM, — відкритий гаманець. Профіль ``local`` навмисне м'який,
        профіль ``prod`` — ні.
        """
        if not self.is_prod:
            return
        problems = []
        if not self.api_keys:
            problems.append("API_KEYS порожній — публічний ендпоінт без автентифікації")
        if not self.database_url:
            problems.append("DATABASE_URL порожній")
        if not self.redis_url:
            problems.append("REDIS_URL порожній — ліміти й бюджет не працюватимуть")
        if not self.has_real_llm and not self.allow_fake_llm:
            problems.append(
                "LLM_BASE_URL/LLM_API_KEY порожні — у prod FakeLLM не має сенсу. "
                "Якщо це навмисно (локальна перевірка prod-адаптерів) — ALLOW_FAKE_LLM=1"
            )
        if problems:
            raise ConfigError(
                "профіль prod налаштований небезпечно:\n  - " + "\n  - ".join(problems)
            )


settings = Settings.load()
