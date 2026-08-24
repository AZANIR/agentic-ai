"""Три воротарі: хто ти, скільки разів, за чий рахунок.

Це **не одна річ під назвою «безпека»**. Три різні механізми з трьома різними відмовами, і
плутати їх дорого: клієнт, якому сказали «зачекай», поводиться інакше за того, кому сказали
«тебе не впізнано», і зовсім інакше за того, у кого скінчилися гроші.

**Порядок не довільний:**

    1. хто ти            без цього немає ні за ким рахувати, ні з кого списувати
    2. скільки разів     дешева перевірка перед дорогою
    3. за чий рахунок    рахувати витрати тих, кого однаково відхилять, — марна робота

Ліміт до автентифікації рахував би всіх анонімів як одного клієнта: один зловмисник закривав
би сервіс для решти. Бюджет до ліміту витрачав би облік на відхилених.

**Жоден воротар не доходить до моделі.** Це головна властивість: відмова коштує нуль викликів,
інакше запобіжник, що спрацьовує після витрати, називається звітом.

**Ключ не залишає цього модуля.** Назовні йде похідний ідентифікатор власника, і за ним ключ
не відновлюється. Ключ у трейсі — це ключ у файлі, який читає той, хто налагоджує.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from shared.config import Settings
from shared.counters import DAY, MINUTE, Counters

OK = "ok"
UNAUTHENTICATED = "unauthenticated"
RATE_LIMITED = "rate_limited"
BUDGET_EXHAUSTED = "budget_exhausted"


@dataclass(frozen=True)
class Verdict:
    """Рішення воротарів. `kind` розрізняє відмови — і у відповіді, і в метриках."""

    allowed: bool
    kind: str
    owner: str = ""
    reason: str = ""
    retry_after: float | None = None


def owner_of(key: str) -> str:
    """Похідний ідентифікатор власника. Ключ із нього не відновлюється.

    Він потрапляє у трейс, у метрики й у ключі лічильників — тобто у все, що хтось колись
    прочитає. Сам ключ не потрапляє нікуди (AC-12).
    """
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def authenticate(key: str, settings: Settings) -> Verdict:
    """Перший воротар: чи впізнано ключ.

    Порівняння **стале за часом**. Звичайне `==` завершується на першому розбіжному байті,
    тобто час відповіді розповідає довжину спільного префікса — а це підбір ключа по одному
    символу. Ціна правильного порівняння — одна функція зі стандартної бібліотеки.
    """
    # Порівняння в байтах, не в рядках. `compare_digest` на не-ASCII рядках кидає
    # TypeError — тобто клієнт, що надіслав кирилицю в заголовку, валив би сервіс
    # замість отримати відмову. Заголовок пише хто завгодно; ASCII в ньому — здогад.
    given = key.encode()
    known = any(hmac.compare_digest(given, candidate.encode()) for candidate in settings.api_keys)
    if not known:
        # Формулювання однакове для «немає такого ключа» й «ключ більше не діє». Різниця у
        # відповіді була б оракулом: перебирай, доки текст не зміниться.
        return Verdict(allowed=False, kind=UNAUTHENTICATED, reason="ключ не впізнано")
    return Verdict(allowed=True, kind=OK, owner=owner_of(key))


def within_rate(owner: str, counters: Counters, settings: Settings, *, now: float) -> Verdict:
    """Другий воротар: чи не надто часто.

    Лічильник **на власника**, не на сервіс. Спільний лічильник задовольняє «понад ліміт
    відхилено» дослівно й робить одного клієнта здатним зупинити всіх.
    """
    seen = counters.total(f"rate:{owner}", now=now, window=MINUTE)
    if seen >= settings.rate_limit_per_minute:
        return Verdict(
            allowed=False,
            kind=RATE_LIMITED,
            owner=owner,
            reason=f"{int(seen)} запитів за хвилину при межі {settings.rate_limit_per_minute}",
            retry_after=MINUTE,
        )
    counters.add(f"rate:{owner}", 1, now=now, window=MINUTE)
    return Verdict(allowed=True, kind=OK, owner=owner)


def within_budget(owner: str, counters: Counters, settings: Settings, *, now: float) -> Verdict:
    """Третій воротар: чи лишилися гроші.

    Дві межі: на власника за добу й на сервіс за добу. Друга потрібна, бо перша не рятує від
    десяти власників одночасно — а рахунок приходить один.
    """
    spent = counters.total(f"spend:{owner}", now=now, window=DAY)
    if spent >= settings.budget_usd_per_day:
        return Verdict(
            allowed=False,
            kind=BUDGET_EXHAUSTED,
            owner=owner,
            reason=f"витрачено ${spent:.2f} за добу при межі ${settings.budget_usd_per_day:.2f}",
        )
    return Verdict(allowed=True, kind=OK, owner=owner)


def charge(owner: str, counters: Counters, amount: float, *, now: float) -> float:
    """Записати витрату. Запобіжник, який ніколи не рахує, ніколи й не спрацює."""
    return counters.add(f"spend:{owner}", amount, now=now, window=DAY)


def admit(key: str, counters: Counters, settings: Settings, *, now: float) -> Verdict:
    """Усі три по порядку. Перша відмова — відповідь; далі не йдемо."""
    seen = authenticate(key, settings)
    if not seen.allowed:
        return seen
    for gate in (within_rate, within_budget):
        verdict = gate(seen.owner, counters, settings, now=now)
        if not verdict.allowed:
            return verdict
    return seen
