"""Два виміри, які реалізація не може порахувати сама (ADR-0002, ADR-0003).

**Токени — на межі провайдера.** Лічильник усередині реалізації бачить те, що реалізація
попросила. Саме те, що додав фреймворк, він за побудовою не бачить — а це рівно вимірювана
величина. Тому лічильник обгортає клієнта, отриманого з `shared.llm`, і дивиться на
**фактичний** запит, яким би шаром він не був складений:

    asked     тексти, які прописав контракт
    sent      усе, що поїхало
    overhead  різниця — і є ціною риштувань

Для базової лінії надбавка дорівнює **нулю**: вона відправляє рівно те, що прописав контракт.
Без цієї дзеркальної половини лічильник, який показує надбавку скрізь, не відрізняв би
фреймворк від власного коду.

**Невидимі рядки — трасуванням, а не розміром пакета.** Установлений пакет несе підтримку
десятків інтеграцій, з яких на цьому вході не виконається жодна. Тому міряються рядки, що
**виконались**: скільки коду фреймворка справді працювало за автора.

Межа названа прямо: число описує **цей вхід**. Інша задача виконає інші рядки — це властивість
виміру, а не його вада.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Та сама груба оцінка, що й у підробленої моделі: ~4 символи на токен. Точність тут
# недосяжна й не потрібна — потрібна одна одиниця на всі чотири реалізації.
CHARS_PER_TOKEN = 4


def tokens(value: str) -> int:
    return max(1, len(value) // CHARS_PER_TOKEN) if value else 0


@dataclass
class Tally:
    """Скільки просив контракт і скільки пішло насправді. Тексту запиту тут немає."""

    asked: int = 0
    sent: int = 0
    calls: int = 0
    # Тексти, які контракт визнає своїми. Усе інше в запиті — надбавка.
    owned: frozenset[str] = field(default_factory=frozenset)

    @property
    def overhead(self) -> int:
        """Ціна риштувань: усе, що поїхало понад прописане контрактом."""
        # Інваріант, а не кліп. `max(0, …)` тут був недосяжною гілкою, що вдавала
        # запобіжник: `asked` росте лише там, де вже виріс `sent`. Кліп, який не може
        # спрацювати, ховає ту єдину подію, заради якої його ставлять.
        assert self.sent >= self.asked, (self.sent, self.asked)
        return self.sent - self.asked

    def observe(self, payload: dict[str, Any]) -> None:
        """Порахувати один запит до моделі. Зберігаються **числа**, не текст (spec §6.1)."""
        self.calls += 1
        for part in _texts(payload):
            self.sent += tokens(part)
            # Контрактний текст зараховується і як ПІДРЯДОК: фреймворк ролей вкладає
            # промпт задачі всередину більшого рядка («Current Task: …»), і точний збіг
            # порахував би весь контракт надбавкою — тобто звинуватив би фреймворк у
            # тому, що написав автор.
            #
            # Береться НАЙДОВШИЙ збіг, а не сума: контрактні тексти вкладені один в
            # одного (питання живе всередині промпту), і сума порахувала б їх двічі —
            # `asked` перевищив би `sent`, тобто надбавка стала б відʼємною.
            matched = [tokens(owned) for owned in self.owned if owned in part]
            self.asked += min(max(matched, default=0), tokens(part))


def _texts(payload: dict[str, Any]) -> list[str]:
    """Текстові частини запиту: вміст повідомлень і описи інструментів.

    Обгортка ролей (`{"role": "user"}`) не рахується навмисно: вона однакова в усіх і
    зробила б надбавку базової лінії ненульовою, тобто зіпсувала б дзеркальну половину.
    """
    found: list[str] = []
    for message in payload.get("messages") or []:
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and content:
            found.append(content)
        elif isinstance(content, list):
            found += [part.get("text", "") for part in content if isinstance(part, dict)]
    for tool in payload.get("tools") or []:
        # Перевіряється тип ВНУТРІШНЬОГО значення, а не лише зовнішнього. Фреймворк може
        # надіслати `{"type": "function", "function": "search_notes"}`, і тоді `.get()` на
        # рядку валить прогін просто на межі провайдера — етап 4 уже платив за цей клас.
        function = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function, dict):
            continue
        if description := function.get("description"):
            found.append(description)
    return [part for part in found if part]


class _CountedCompletions:
    def __init__(self, inner: Any, tally: Tally) -> None:
        self._inner, self._tally = inner, tally

    def create(self, **kwargs: Any) -> Any:
        self._tally.observe(kwargs)
        return self._inner.create(**kwargs)


class _CountedChat:
    def __init__(self, inner: Any, tally: Tally) -> None:
        self.completions = _CountedCompletions(inner.completions, tally)


class CountedClient:
    """Клієнт, крізь який усе видно. Форма та сама, тож фреймворк різниці не помічає.

    Делегує будь-який інший атрибут усередину: реалізація, що дотягнеться до чогось, чого
    тут не передбачено, має працювати, а не впасти на обгортці лічильника.
    """

    def __init__(self, inner: Any, tally: Tally) -> None:
        self._inner = inner
        self.tally = tally
        self.chat = _CountedChat(inner.chat, tally)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def counted(inner: Any, owned: frozenset[str]) -> CountedClient:
    """Обгорнути клієнта лічильником. Єдиний спосіб побачити надбавку фреймворка."""
    return CountedClient(inner, Tally(owned=owned))


@contextmanager
def executed_lines(*packages: str) -> Iterator[set[tuple[str, int]]]:
    """Зібрати рядки названих пакетів, що **виконались** усередині блоку.

    `sys.settrace` дорогий, і саме тому облік вмикається лише навколо прогону однієї
    реалізації, а не на весь набір. На підробленій моделі це коштує мілісекунди.

    Пакети шукаються за **шляхом файлу**, а не за іменем модуля: фреймворк виконує код
    своїх залежностей теж, і рядок із `langchain_core` — це так само не мій рядок.

    **Дві названі межі.** Число описує **цей вхід**: інша задача виконає інші рядки.
    І воно бачить лише **цей потік**: `sys.settrace` не поширюється на інші, тож
    реалізація, що робить роботу в окремому потоці, дасть нуль — тихо. Обидві межі
    названі тут, а не з'ясовуються під час читання таблиці.
    """
    # Роздільник у кінці кореня обовʼязковий: `…/site-packages/langgraph` як префікс
    # збігається і з `…/langgraph_sdk`, що лежить поруч. Тихий перебір у головній
    # колонці — дзеркало тієї самої вади з `origin`, якою етап пишається.
    roots = tuple(_root(name) for name in packages)
    roots = tuple(root + os.sep for root in roots if root)
    seen: set[tuple[str, int]] = set()
    if not roots:
        yield seen
        return

    def _trace(frame: Any, event: str, _arg: Any) -> Any:
        if event == "line":
            name = frame.f_code.co_filename
            if any(name.startswith(root) for root in roots):
                seen.add((name, frame.f_lineno))
        return _trace

    previous = sys.gettrace()
    sys.settrace(_trace)
    try:
        yield seen
    finally:
        sys.settrace(previous)


def _root(package: str) -> str:
    """Каталог встановленого пакета, або порожньо, якщо його немає.

    `submodule_search_locations` **перед** `origin`: `langgraph` — namespace-пакет, у якого
    `origin` дорівнює `None`. Перша редакція дивилась лише на `origin` і мовчки віддавала
    порожній корінь — тобто недорахувала б невидимі рядки **до нуля** й показала б фреймворк
    безкоштовним. Тихий нуль у колонці, яка існує саме щоб не бути нулем.
    """
    from importlib.util import find_spec  # noqa: PLC0415

    try:
        spec = find_spec(package)
    except (ImportError, ValueError, ModuleNotFoundError):
        return ""
    if spec is None:
        return ""
    if locations := list(spec.submodule_search_locations or []):
        return str(Path(locations[0]))
    return str(Path(spec.origin).parent) if spec.origin else ""
