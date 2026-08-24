"""Детермінований підробний LLM — інструмент навчання, а не мок заради тесту (ADR-0006).

Навіщо він існує. Справжня модель недетермінована, платна і потребує мережі. Це робить
неможливими саме ті перевірки, які найважливіші: «чи спрацював ліміт кроків», «чи впіймали
криві аргументи», «чи не пішов агент по колу». Підробка розігрує заздалегідь записаний
сценарій, тож така перевірка стає можливою — і безкоштовною.

Форма відповіді навмисне збігається з OpenAI SDK до останнього поля, включно з тим, що
``function.arguments`` — це РЯДОК JSON, а не словник. Якби підробка «полагодила» цю
незручність, код етапу перестав би працювати зі справжнім провайдером.

    from shared.fake_llm import FakeLLM, text, tool_call

    client = FakeLLM([
        tool_call("get_weather", {"city": "Bengaluru"}),
        text("У Бенгалуру 28°C, хмарно."),
    ])
    response = client.chat.completions.create(model="fake", messages=[...])
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


class FakeLLMError(RuntimeError):
    """Сценарій вичерпано або використано неправильно."""


# --- об'єкти відповіді: та сама форма, що й у openai SDK ---------------------


@dataclass
class FakeFunction:
    name: str
    arguments: str  # рядок JSON — саме так, як віддає справжній SDK


@dataclass
class FakeToolCall:
    id: str
    function: FakeFunction
    type: str = "function"


@dataclass
class FakeMessage:
    role: str = "assistant"
    content: str | None = None
    tool_calls: list[FakeToolCall] | None = None

    def model_dump(self) -> dict[str, Any]:
        """Сумісність із pydantic-моделлю справжнього SDK."""
        out: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            out["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in self.tool_calls
            ]
        return out


@dataclass
class FakeChoice:
    message: FakeMessage
    index: int = 0
    finish_reason: str = "stop"


@dataclass
class FakeUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class FakeResponse:
    choices: list[FakeChoice]
    usage: FakeUsage
    model: str = "fake"


# --- конструктори кроків сценарію -------------------------------------------


def text(content: str) -> dict[str, Any]:
    """Крок сценарію: модель відповідає текстом і зупиняється."""
    return {"kind": "text", "content": content}


def tool_call(name: str, arguments: dict[str, Any] | str) -> dict[str, Any]:
    """Крок сценарію: модель просить викликати один інструмент."""
    return {"kind": "tools", "calls": [(name, arguments)]}


def tool_calls(*calls: tuple[str, dict[str, Any] | str]) -> dict[str, Any]:
    """Крок сценарію: модель просить кілька інструментів одразу (паралельні виклики)."""
    return {"kind": "tools", "calls": list(calls)}


# --- сам підробний клієнт ----------------------------------------------------


def _estimate_tokens(value: Any) -> int:
    """Груба оцінка: ~4 символи на токен.

    Точність тут не потрібна й недосяжна. Потрібна лише НЕНУЛЬОВА, монотонна
    величина, щоб бюджетний запобіжник і підрахунок токенів на етапі 8 мали
    що рахувати в офлайні.
    """
    return max(1, len(json.dumps(value, ensure_ascii=False, default=str)) // 4)


# Слова, за якими видно, ЩО в промпта питають. Не розуміння — розпізнавання форми.
_CATEGORIES = ("orders", "knowledge", "math")
_JUDGING = ("чи відповідає", "оціни", "так або ні", "достатньо")


def _pretend_to_classify(prompt: str) -> str:
    """Обрати категорію за ознаками запиту. Груба евристика — і чесно груба.

    Справжня модель читає зміст; підробка читає ознаки. Вистачає рівно на те, щоб демо
    показувало **три різні гілки** там, де обіцяє три різні гілки.

    Дивиться на **останній рядок** промпту, а не на весь. Перша редакція читала все — і
    відносила все до `orders`, бо самий опис категорій містить слова «замовлення» й
    «повернення». Тобто евристика впізнавала шаблон замість запиту, і демо друкувало три
    однакові гілки під заголовком «три різні гілки».

    Звʼязок із форматом промпту тут є, і він названий: запит стоїть останнім рядком.
    Це припущення підробки, а не властивість коду — справжній провайдер читає все.
    """
    body = prompt.strip()
    asked = body.splitlines()[-1] if body else ""
    if "ord_" in asked or "замовлен" in asked:
        return "orders"
    if any(word in asked for word in ("порахуй", "скільки буде", "плюс", "мінус", "додай")):
        return "math"
    return "knowledge"


def _auto_step(request: dict[str, Any]) -> dict[str, Any]:
    """Відповідь на промпт, якого ніхто не передбачав.

    **Це не модель і не імітація моделі.** Це розпізнавання форми запиту: якщо промпт
    перелічує категорії — назвати категорію; якщо просить оцінити — сказати «так»;
    інакше — речення тексту.

    Навіщо: сервіс має підніматись і відповідати **без платного ключа**, інакше правило
    курсу «усе працює офлайн» перестає діяти рівно там, де етап найбільший. Сценарій
    тут неможливий за побудовою — запити пише користувач, а не автор перевірки.

    **Межа названа чесно.** Відповіді беззмістовні: вони мають правильну ФОРМУ й нульовий
    зміст. Демонстрація конвеєра — так; демонстрація якості відповідей — ні, і жодна
    перевірка цього не стверджує.
    """
    messages = request.get("messages") or []
    prompt = " ".join(str(m.get("content") or "") for m in messages).lower()

    if all(name in prompt for name in _CATEGORIES):
        # Промпт перелічує всі категорії — отже, просить обрати одну. Підробка тут
        # **грає роль моделі**, тож обирати однаково для всього означало б показувати
        # читачеві зламаний класифікатор і називати це роботою.
        #
        # Це не суперечить ADR-0001, який відхилив класифікацію за ключовими словами:
        # там ішлося про поведінку СЕРВІСУ при вичерпаному бюджеті. Тут ключові слова —
        # усередині підробленого провайдера, тобто на місці моделі, а не замість неї.
        return text(_pretend_to_classify(prompt))
    if any(word in prompt for word in _JUDGING):
        return text("так")
    return text("Відповідь підробленого провайдера: змісту тут немає за побудовою.")


@dataclass
class FakeLLM:
    """Підробний OpenAI-сумісний клієнт, що розігрує заданий сценарій.

    :param script: кроки, створені через :func:`text` / :func:`tool_call` / :func:`tool_calls`
    :param repeat_last: коли сценарій вичерпано — повторювати останній крок нескінченно.
        Саме цим перевіряється ліміт кроків агента: підробка, що ЗАВЖДИ просить інструмент,
        доводить, що зупиняє агента саме ліміт, а не збіг обставин.
    """

    script: list[dict[str, Any]] = field(default_factory=list)
    # Відповідати на будь-який промпт, коли сценарій вичерпано. Потрібно рівно там,
    # де запитів **наперед не знають**: у сервісі кожен запит інший, тож сценарій
    # неможливий за побудовою. Ціна названа у `_auto_step`.
    auto_reply: bool = False
    repeat_last: bool = False
    calls: list[dict[str, Any]] = field(default_factory=list, init=False)
    _cursor: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.chat = _Chat(self)

    @classmethod
    def always_calling(cls, name: str, arguments: dict[str, Any] | None = None) -> FakeLLM:
        """Підробка, що нескінченно просить один і той самий інструмент."""
        return cls(script=[tool_call(name, arguments or {})], repeat_last=True)

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def _next_step(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.auto_reply and self._cursor >= len(self.script):
            return _auto_step(request or {})
        if self._cursor < len(self.script):
            step = self.script[self._cursor]
            self._cursor += 1
            return step
        if self.repeat_last and self.script:
            return self.script[-1]
        raise FakeLLMError(
            f"сценарій вичерпано: у ньому {len(self.script)} кроків, "
            f"а модель викликали {self.call_count} разів. "
            "Або допиши крок, або постав repeat_last=True."
        )

    def _build(self, step: dict[str, Any], request: dict[str, Any]) -> FakeResponse:
        prompt_tokens = _estimate_tokens(request.get("messages", []))
        if step["kind"] == "text":
            message = FakeMessage(content=step["content"])
            finish = "stop"
            completion_tokens = _estimate_tokens(step["content"])
        else:
            made = []
            for index, (name, arguments) in enumerate(step["calls"]):
                raw = (
                    arguments
                    if isinstance(arguments, str)
                    else json.dumps(arguments, ensure_ascii=False)
                )
                made.append(
                    FakeToolCall(
                        id=f"call_{self.call_count}_{index}",
                        function=FakeFunction(name=name, arguments=raw),
                    )
                )
            message = FakeMessage(content=None, tool_calls=made)
            finish = "tool_calls"
            completion_tokens = _estimate_tokens(step["calls"])
        return FakeResponse(
            choices=[FakeChoice(message=message, finish_reason=finish)],
            usage=FakeUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
            model=str(request.get("model", "fake")),
        )


@dataclass
class _Chat:
    client: FakeLLM

    def __post_init__(self) -> None:
        self.completions = _Completions(self.client)


@dataclass
class _Completions:
    client: FakeLLM

    def create(self, **kwargs: Any) -> FakeResponse:
        self.client.calls.append(kwargs)
        return self.client._build(self.client._next_step(kwargs), kwargs)
