"""Адаптер ембеддингів — той самий патерн, що й LLM-клієнт (ADR репозиторію 0002).

Ембеддинг — це список чисел, який представляє зміст тексту. Уся ідея пошуку тримається на
одній властивості: **близькі за змістом тексти мають близькі списки**. Наскільки близькі —
міряє косинус між ними.

За замовчуванням тут стоїть **хеш за словами**: кожне слово дає позицію у векторі, вага —
скільки разів воно трапилось. Це навмисно слабкий ембеддер, і слабкий він у конкретний,
корисний спосіб:

    «скільки днів на повернення»  ->  знаходить документ про повернення   (спільні слова)
    «як оформити відмову»          ->  не знаходить нічого                (жодного спільного слова)

Ця межа — не вада реалізації, а зміст уроку. Хороший навчальний ембеддер має ламатися видимо,
інакше читач не зрозуміє, навіщо колись переходити на справжній (ADR етапу 0001).

Українська морфологія б'є сильніше за англійську: «повернення» й «повернень» тут різні слова.
Про це урок каже прямо — це та сама межа, лише ближче до дому.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from shared.config import ConfigError, Settings
from shared.config import settings as default_settings

DIMENSIONS = 256
_WORD = re.compile(r"\w+", re.UNICODE)


class Embedder(Protocol):
    """Спільний інтерфейс. Код етапів знає лише його."""

    name: str

    def embed(self, texts: list[str]) -> np.ndarray:
        """Повернути матрицю нормованих векторів, по рядку на текст."""
        ...


@dataclass
class HashEmbedder:
    """Детермінований ембеддер за словами. Ані мережі, ані моделі, ані завантажень."""

    dimensions: int = DIMENSIONS
    name: str = "hash-words"

    def _slot(self, word: str) -> int:
        # sha1, а не вбудований hash(): той рандомізується між процесами, і перевірки
        # ставали б мигтливими без жодної зміни коду.
        digest = hashlib.sha1(word.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self.dimensions

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dimensions), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in _WORD.findall(text.lower()):
                matrix[row, self._slot(word)] += 1.0
        # Нормуємо: без цього довгий документ вигравав би просто через довжину, а не
        # через доречність. Після нормування косинус — це звичайний скалярний добуток.
        lengths = np.linalg.norm(matrix, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        return matrix / lengths


@dataclass
class FastEmbedEmbedder:
    """Справжні локальні ембеддинги на CPU. Вмикається `pip install -e ".[embed]"`."""

    model: str
    name: str = ""

    def __post_init__(self) -> None:
        self.name = f"fastembed:{self.model}"
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise ConfigError(
                "EMBEDDINGS_PROVIDER=fastembed, але пакет не встановлений.\n"
                'Постав його: pip install -e ".[embed]"'
            ) from None
        self._model = TextEmbedding(model_name=self.model)

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.array(list(self._model.embed(texts)), dtype=np.float32)
        lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        return vectors / lengths


@dataclass
class ApiEmbedder:
    """Ембеддинги через OpenAI-сумісного провайдера — той самий `base_url`, що й для моделі."""

    model: str
    settings: Settings
    name: str = ""

    def __post_init__(self) -> None:
        self.name = f"api:{self.model}"

    def embed(self, texts: list[str]) -> np.ndarray:
        from shared.llm import make_client

        response = make_client(self.settings).embeddings.create(model=self.model, input=texts)
        vectors = np.array([item.embedding for item in response.data], dtype=np.float32)
        lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        return vectors / lengths


def get_embedder(settings: Settings | None = None) -> Embedder:
    """Повернути ембеддер за конфігурацією. Дефолт — хеш: офлайн, детермінований, без ключа."""
    settings = settings or default_settings
    provider = settings.embeddings_provider

    if provider == "hash":
        return HashEmbedder()
    if provider == "fastembed":
        return FastEmbedEmbedder(model=settings.embeddings_model or "BAAI/bge-small-en-v1.5")
    if provider == "openai":
        if not settings.has_real_llm:
            raise ConfigError(
                "EMBEDDINGS_PROVIDER=openai, але LLM_BASE_URL/LLM_API_KEY порожні — "
                "ембеддинги йдуть через того самого провайдера, що й модель."
            )
        return ApiEmbedder(
            model=settings.embeddings_model or "text-embedding-3-small", settings=settings
        )
    raise ConfigError(
        f"Невідомий EMBEDDINGS_PROVIDER={provider!r}. Доступні: hash, fastembed, openai."
    )


def cosine(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Косинусна близькість запиту до кожного рядка матриці.

    Оскільки всі вектори нормовані, це просто скалярний добуток — саме тому нормування
    вище не косметика, а те, що робить цей рядок правильним.
    """
    return matrix @ query
