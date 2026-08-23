"""Індекс, косинусна близькість, поріг і фільтр доступу.

Уся «магія» retrieval вміщається у два рядки: порахувати близькість запиту до кожного
фрагмента й відсортувати. Решта модуля — три речі навколо цих двох рядків, і кожна з них
розв'язує проблему, якої сам пошук не бачить:

    поріг         відрізняє «знайшлося погане» від «не знайшлося»
    top-k         обмежує, скільки з відсортованого йде далі
    фільтр        прибирає те, чого питальнику не можна бачити

**Порядок останніх двох — не деталь реалізації.** Фільтр стоїть ДО відбору top-k, і це
рішення записане окремим ADR (етапу 0002). Якщо поставити його після, внутрішній документ
займає слот у видачі, потім його прибирають — і питальник отримує «нічого не знайдено»
замість правильної відповіді, яка була третьою. Витоку немає; відповідь зникла.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from shared.embeddings import Embedder, cosine
from stages.s02_rag.chunk import Fragment, split
from stages.s02_rag.documents import NO_FILTER, Document


@dataclass
class IndexReport:
    """Що саме потрапило в індекс і що довелося пропустити."""

    indexed: int = 0
    fragments: int = 0
    skipped: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Hit:
    fragment: Fragment
    score: float


@dataclass
class SearchResult:
    """Результат пошуку разом із тим, ЧОМУ він такий."""

    hits: list[Hit]
    closest: list[Hit]
    threshold: float
    filtered_out: int = 0

    @property
    def below_threshold(self) -> bool:
        """Щось знайшлося, але надто далеке. Це стан, а не збій."""
        return not self.hits and bool(self.closest)

    @property
    def best_score(self) -> float:
        pool = self.hits or self.closest
        return pool[0].score if pool else 0.0


class KnowledgeBase:
    """База знань у пам'яті: індексує фрагменти й шукає по них."""

    def __init__(self, *, embedder: Embedder, threshold: float = 0.2) -> None:
        self.embedder = embedder
        self.threshold = threshold
        self.fragments: list[Fragment] = []
        self.access: list[str] = []
        self.vectors: np.ndarray | None = None
        self.report = IndexReport()

    def index(self, documents: list[Document], *, size: int, overlap: int = 0) -> IndexReport:
        """Порізати, порахувати вектори, запам'ятати рівень доступу кожного фрагмента.

        Зіпсований документ **називається й пропускається**. Один порожній файл не має
        робити всю базу недоступною — це та сама fail-safe логіка, що й на етапі 1.
        """
        report = IndexReport()
        # Індексація замінює вміст, а не додає до нього: інакше повторний виклик подвоює
        # базу, і дублікат з'їдає слот у top-k, не сказавши про це жодним словом.
        self.fragments.clear()
        self.access.clear()
        for document in documents:
            pieces = split(document.body, source=document.name, size=size, overlap=overlap)
            if not pieces:
                report.skipped[document.name] = "порожній або без придатного тексту"
                continue
            self.fragments.extend(pieces)
            self.access.extend([document.access] * len(pieces))
            report.indexed += 1
            report.fragments += len(pieces)

        self.vectors = (
            self.embedder.embed([f.text for f in self.fragments])
            if self.fragments
            else np.zeros((0, 1), dtype=np.float32)
        )
        self.report = report
        return report

    def search(self, query: str, *, access: str, top_k: int = 3) -> SearchResult:
        """Знайти найближчі фрагменти, які питальнику дозволено бачити.

        :param access: рівень доступу питальника, або ``NO_FILTER`` — названий сентинел
            «показати все», потрібний демонстрації межі. ``None`` заборонено навмисно:
            це значення дає будь-яка нерозв'язана резолюція «хто питає», і пропустити
            його означало б відкрити базу тому, кого не вдалося впізнати.
        """
        if access is None:
            raise ValueError(
                "access=None заборонено: невпізнаний питальник не отримує повного доступу. "
                f"Передай рівень доступу або {NO_FILTER!r}, якщо фільтр справді не потрібен."
            )
        if top_k < 1:
            raise ValueError(f"top_k={top_k} має бути щонайменше 1")
        if self.vectors is None or not self.fragments:
            return SearchResult(hits=[], closest=[], threshold=self.threshold)

        scores = cosine(self.embedder.embed([query])[0], self.vectors)

        # --- фільтр доступу. ДО відбору top-k, і саме в цьому вся справа (ADR-0002).
        allowed = [
            i for i in range(len(self.fragments)) if access == NO_FILTER or self.access[i] == access
        ]
        filtered_out = len(self.fragments) - len(allowed)

        ranked = sorted(allowed, key=lambda i: float(scores[i]), reverse=True)
        closest = [Hit(self.fragments[i], float(scores[i])) for i in ranked[:top_k]]
        hits = [hit for hit in closest if hit.score >= self.threshold]

        return SearchResult(
            hits=hits,
            closest=closest,
            threshold=self.threshold,
            filtered_out=filtered_out,
        )
