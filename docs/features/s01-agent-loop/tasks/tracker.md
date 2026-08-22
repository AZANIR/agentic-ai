# Tracker — s01-agent-loop

> Статус кожної задачі епіку. `implement` оновлює `done` у міру коммітів.
> Стани: `todo` · `in_progress` · `blocked` · `review` · `done`.

| # | Task | Layer | Owner | Estimate | Blocked by | Status |
|---|---|---|---|---|---|---|
| T1 | Реєстр трьох інструментів зі схемами й познакою незворотності | app | Contributor | S | — | done |
| T2 | Валідація аргументів інструмента проти оголошеної схеми | app | Contributor | S | — | done |
| T3 | Цикл ReAct із трасуванням і лімітом кроків | app | Contributor | M | T1, T2 | done |
| T4 | Гейт підтвердження незворотної дії | app | Contributor | S | T3 | done |
| T5 | Демо: чотири сценарії підряд і банер джерела відповідей | ports | Contributor | M | T3, T4 | done |
| T6 | Перевірки етапу: щасливі шляхи і три режими відмови | tests | Contributor | M | T3, T4 | done |
| T7 | Урок етапу: канон статті, міст на NovaShop, «що зламати» | docs | Contributor | M | T5, T6 | done |
| T8 | Вправи, еталонні розв'язки й чекліст етапу | docs | Contributor | S | T7 | done |
| T9 | Терміни етапу в глосарій, статус етапу в програму | docs | Contributor | S | T7 | todo |

**Total:** 9 задач, ~6.5 людино-днів.

Паралельні гілки: T1 і T2 стартують одночасно (спільних файлів немає). T5 і T6 —
після T4, теж паралельно. T8 і T9 — після T7, паралельно.
