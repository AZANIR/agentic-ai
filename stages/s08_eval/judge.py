"""Суддя-модель — і те, чому його вердикт не є істиною (ADR-0002).

**Два протоколи, не один.** Попарний і поточковий міряють різне й потрібні різному:

    compare(задача, перша, друга) -> хто переміг    ловить position bias
    score(задача, відповідь, еталон) -> бал          ловить length bias

У попарному немає **бала**, у поточковому немає **порядку**. Один протокол не показав би
обох біасів, і саме тому їх два.

**Підроблений суддя упереджений навмисно.** Він не імітує конкретну модель — він грає роль
**зламаного приладу**, так само як мутація грає роль зламаного коду. Без нього доказ етапу
неможливий офлайн, а з ним доказ відтворюваний і детермінований.

Що саме він робить не так, сказано тут, а не заховано:

    позиційна надбавка   перша з поданих отримує безкоштовний бал
    надбавка за довжину  кожні кілька символів додають бал незалежно від змісту

**Підробка не доводить, що справжні судді упереджені.** Це показано в літературі. Вона дає
**детекторові що виявляти**. З ключем той самий детектор іде проти справжньої моделі.

**Лічильник викликів — не діагностика, а частина контракту** (AC-04). Детермінований
оцінювач має показати нуль; інакше «суддя лише там, де потрібне судження» лишається
побажанням.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

FIRST = "перша"
SECOND = "друга"
TIE = "нічия"

# Шкала бала. Ціла й названа: «вищий бал» без шкали — це не число, а враження.
SCALE = 10

# Скільки безкоштовних балів дає позиція. Причина, з якої перестановка міняє вердикт.
POSITION_BONUS = 2
# Скільки символів зайвого тексту коштують одного бала.
CHARS_PER_POINT = 40


class Unavailable(Exception):
    """Суддя не зміг винести вердикт. Це **не** провал кейса, а третій стан (AC-08)."""


# Закритий перелік причин, за яких прилад вважається недоступним. Провайдери не мають
# спільної ієрархії винятків, тож розпізнаємо і за типом, і за словом у повідомленні —
# але **лише** за названим, а не за фактом винятку.
UNAVAILABLE_TYPES = ("Timeout", "RateLimit", "Connection", "APIStatus", "APIConnection")
UNAVAILABLE_WORDS = ("quota", "rate limit", "rate_limit", "timeout", "overloaded", "budget")


def _is_unavailable(error: Exception) -> bool:
    """Чи належить ця відмова до закритого переліку «прилад недоступний».

    Нова причина відмови провайдера сюди не потрапить — і **читатиметься як провал**,
    навмисно гучно, доки її не додадуть правкою (spec §8).
    """
    if isinstance(error, TimeoutError | ConnectionError):
        return True
    named = type(error).__name__
    if any(word in named for word in UNAVAILABLE_TYPES):
        return True
    return any(word in str(error).lower() for word in UNAVAILABLE_WORDS)


@dataclass(frozen=True)
class Compared:
    """Хто переміг у попарному порівнянні. Нічия — окреме значення, не відсутність."""

    winner: str
    reason: str


@dataclass(frozen=True)
class Scored:
    """Бал за оголошеною шкалою."""

    score: int
    reason: str


class Judge(Protocol):
    name: str
    calls: int

    def compare(self, task: str, first: str, second: str, *, expected: str = "") -> Compared: ...

    def score(self, task: str, answer: str, expected: str) -> Scored: ...


# Скільки початкових літер порівнювати. Українська відмінює: «пароль» проти «паролі»,
# «Банкова» проти «Банкову». Точний перетин множин дав би нуль там, де людина бачить
# збіг, — і саме на цьому вже спіткнувся етап 5 (PLAYBOOK §5).
STEM = 5


def _words(text: str) -> set[str]:
    """Значущі слова. Пунктуація знімається **до** відсіву за довжиною.

    Порядок не косметичний: `«три»` проходив як чотирисимвольний, а `три` — ні, тож суддя
    не відрізняв три місяці від пʼяти залежно від того, чи стояла поруч крапка.
    """
    stripped = (word.lower().strip(".,!?:;»«()") for word in text.split())
    return {word for word in stripped if len(word) > 3}


def _grounded(answer: str, expected: str) -> int:
    """Скільки понять еталона згадано у відповіді. Порівняння за основою слова."""
    if not expected:
        return 0
    said = _words(answer)
    return sum(
        1
        for want in _words(expected)
        if any(s.startswith(want[:STEM]) or want.startswith(s[:STEM]) for s in said)
    )


@dataclass
class BiasedJudge:
    """Суддя зі **задокументованою** упередженістю. Роль: зламаний прилад."""

    name: str = "biased-fake"
    calls: int = 0
    position_bonus: int = POSITION_BONUS
    chars_per_point: int = CHARS_PER_POINT

    def _points(self, answer: str, expected: str) -> int:
        """Зміст плюс надбавка за довжину. Друге не має впливати, і в цьому вся річ."""
        return _grounded(answer, expected) + len(answer) // self.chars_per_point

    def compare(self, task: str, first: str, second: str, *, expected: str = "") -> Compared:
        self.calls += 1
        left = self._points(first, expected) + self.position_bonus
        right = self._points(second, expected)
        if left == right:
            return Compared(TIE, "однаково")
        winner = FIRST if left > right else SECOND
        return Compared(winner, f"{left} проти {right}")

    def score(self, task: str, answer: str, expected: str) -> Scored:
        self.calls += 1
        points = min(SCALE, self._points(answer, expected))
        return Scored(points, f"{points} із {SCALE}")


@dataclass
class SteadyJudge:
    """Суддя, чий вердикт не залежить ані від порядку, ані від довжини.

    Потрібен **дзеркальній** половині AC-05b: детектор, що знаходить біас завжди, не
    відрізняє упередженого суддю від чесного й тому не є детектором.
    """

    name: str = "steady-fake"
    calls: int = 0

    def compare(self, task: str, first: str, second: str, *, expected: str = "") -> Compared:
        self.calls += 1
        left, right = _grounded(first, expected), _grounded(second, expected)
        if left == right:
            return Compared(TIE, "однаково обґрунтовані")
        return Compared(FIRST if left > right else SECOND, f"{left} проти {right}")

    def score(self, task: str, answer: str, expected: str) -> Scored:
        self.calls += 1
        return Scored(min(SCALE, _grounded(answer, expected)), "лише зміст")


@dataclass
class ModelJudge:
    """Справжній суддя. Без налаштованого провайдера кожен виклик — `Unavailable`."""

    name: str = "model"
    calls: int = 0
    client: Any = None
    _script: list[dict[str, Any]] = field(default_factory=list)

    def _ask(self, prompt: str) -> str:
        from shared.config import ConfigError, settings  # noqa: PLC0415

        if not settings.has_real_llm:
            raise Unavailable("провайдера не налаштовано — судити нема чим")
        try:
            from shared.llm import get_client  # noqa: PLC0415

            self.client = self.client or get_client()
            reply = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
            )
            return reply.choices[0].message.content or ""
        except ConfigError as error:
            raise Unavailable(str(error)) from error
        except Exception as error:
            # Перелік ЗАКРИТИЙ (AC-08). Ловити будь-який виняток означало б, що баг у
            # самому харнесі — `ZeroDivisionError`, `AttributeError` — читається як
            # «прилад недоступний»: тиха зелень замість гучного провалу, тобто рівно та
            # вада, від якої весь етап застерігає.
            if not _is_unavailable(error):
                raise
            raise Unavailable(f"{type(error).__name__}: {error}") from error

    def compare(self, task: str, first: str, second: str, *, expected: str = "") -> Compared:
        self.calls += 1
        said = (
            self._ask(
                f"Задача: {task}{chr(10)}Відповідь 1: {first}{chr(10)}Відповідь 2: {second}"
                f"{chr(10)}Яка краще? Відповідай одним словом: перша, друга або нічия."
            )
            .strip()
            .strip(".,!?:;»«()")
            .lower()
        )
        # ТОЧНИЙ збіг, а не пошук підрядка. Пошук ішов у сталому порядку, тож «перша гірша,
        # перемагає друга» давало `перша` — і `position_sweep` рахував це переворотом.
        # Детектор рапортував біас, породжений власним парсером, на судді, який його не мав.
        winner = said if said in (FIRST, SECOND, TIE) else None
        if winner is None:
            raise Unavailable(f"вердикт нерозбірливий: {said[:60]!r}")
        return Compared(winner, said[:80])

    def score(self, task: str, answer: str, expected: str) -> Scored:
        self.calls += 1
        said = self._ask(
            f"Задача: {task}{chr(10)}Відповідь: {answer}{chr(10)}Має покривати: {expected}"
            f"{chr(10)}Постав бал від 0 до {SCALE}. Відповідай самим числом."
        ).strip()
        # Одне ціле число, і нічого крім нього. Попередня редакція збирала ВСІ цифри
        # рядка, тож «оцінка: 3 з 10» ставало `int("310"[:2])` = 10, а «0 з 10» — 1.
        # Промпт сам називає шкалу, тож її повторення — найімовірніша форма відповіді,
        # і суддя, що каже «три з десяти», читався як найвищий бал.
        number = re.fullmatch(r"(\d{1,2})", said)
        if number is None:
            raise Unavailable(f"бал нерозбірливий: {said[:60]!r}")
        return Scored(min(SCALE, int(number.group(1))), said[:80])


def get_judge(*, real: bool = False) -> Judge:
    """Суддя за режимом. Дефолт — упереджена підробка: етап проходиться без ключа.

    `SteadyJudge` тут немає навмисно: він потрібен лише дзеркальній половині детектора й
    створюється там прямо. Фабрика з гілкою, якою ніхто не користується, — це розгалуження,
    що вдає вибір.
    """
    return ModelJudge() if real else BiasedJudge()
