"""Вікно поточної розмови й підсумок того, що з нього витіснено.

Короткочасна памʼять розвʼязує задачу, яку часто плутають із довготривалою: **що сказали в
цій розмові**. Вона не переживає сесію й не має цього робити — те, що варто памʼятати
назавжди, витягується окремо (`long_term`).

Механіка проста: останні N повідомлень лишаються **дослівно**, усе старіше стискається в
підсумок. Дослівний хвіст важливий: модель має бачити точні слова останніх реплік, бо саме
на них вона відповідає. Переказ трьох останніх повідомлень — це втрата там, де втрачати
нічого не треба.

**Головна пастка — стиснути підсумок удруге.** Розмова переповнилась, ми стиснули; далі вона
переповнилась знову, і найпростіша реалізація бере «все, що поза вікном» — разом із
попереднім підсумком — і стискає ще раз.

Наслідок неможливо помітити на око: текст лишається звʼязним і поступово перестає бути
правдою. Кожне стиснення втрачає деталі, і після третього підсумок описує розмову, якої не
було. Тому підсумок **накопичується**, а стискаються тільки нові витіснені повідомлення.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared.llm import get_model

SUMMARY_LABEL = "=== РАНІШЕ В РОЗМОВІ (переказ) ==="
RECENT_LABEL = "=== ОСТАННІ РЕПЛІКИ (дослівно) ==="

_PROMPT = """Стисни ці репліки розмови в кілька речень. Зберігай факти й числа, прибирай
ввічливість і повтори. Пиши українською, від третьої особи.

{lines}"""


@dataclass
class Compression:
    """Що саме сталося при стисненні. Числа, а не «частину скорочено»."""

    compressed: int = 0
    kept: int = 0
    summary: str = ""


@dataclass
class Window:
    """Вікно розмови: дослівний хвіст плюс накопичений переказ витісненого."""

    size: int = 8
    messages: list[dict[str, str]] = field(default_factory=list)
    summary: str = ""

    def add(self, message: dict[str, str]) -> None:
        self.messages.append(message)

    def recent(self) -> list[dict[str, str]]:
        """Останні `size` повідомлень — те, що модель побачить дослівно."""
        return self.messages[-self.size :]

    def overflow(self) -> list[dict[str, str]]:
        """Витіснене з вікна. Підсумку тут немає: він уже стиснутий один раз."""
        return self.messages[: -self.size] if len(self.messages) > self.size else []

    def compress(self, *, client: Any, model: str | None = None) -> Compression:
        """Стиснути витіснене й **дописати** до підсумку, а не переписати його."""
        older = self.overflow()
        if not older:
            return Compression(compressed=0, kept=len(self.messages), summary=self.summary)

        lines = "\n".join(f"- {m['role']}: {m['content']}" for m in older)
        reply = client.chat.completions.create(
            model=model or get_model(),
            messages=[{"role": "user", "content": _PROMPT.format(lines=lines)}],
        )
        addition = (reply.choices[0].message.content or "").strip()

        # Накопичуємо. Попередній підсумок сюди не потрапляв і не потрапить.
        self.summary = f"{self.summary}\n{addition}".strip() if self.summary else addition
        self.messages = self.recent()
        return Compression(compressed=len(older), kept=len(self.messages), summary=self.summary)

    def as_prompt(self) -> str:
        """Розмова для моделі: спершу переказ, потім дослівний хвіст, межа позначена."""
        parts = []
        if self.summary:
            parts.append(f"{SUMMARY_LABEL}\n{self.summary}")
        recent = "\n".join(f"{m['role']}: {m['content']}" for m in self.recent())
        parts.append(f"{RECENT_LABEL}\n{recent}")
        return "\n\n".join(parts)
