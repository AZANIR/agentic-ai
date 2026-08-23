# Tracker — s02-rag

> Стани: `todo` · `in_progress` · `blocked` · `review` · `done`.

| # | Task | Layer | Owner | Estimate | Blocked by | Status |
|---|---|---|---|---|---|---|
| T1 | Адаптер ембеддингів у спільному шарі: hash | fastembed | openai | infra | Contributor | S | — | todo |
| T2 | Нарізка документів на фрагменти | domain | Contributor | S | — | todo |
| T3 | База знань NovaShop із метаданими рівня доступу | domain | Contributor | S | — | todo |
| T4 | Індекс, косинус, top-k, поріг і фільтр доступу | app | Contributor | M | T1, T2, T3 | todo |
| T5 | Складання відповіді з джерелом, яке додає система | app | Contributor | S | T4 | todo |
| T6 | Інструмент пошуку для реєстру агента з етапу 1 | ports | Contributor | S | T4, T5 | todo |
| T7 | Демо: пошук, поріг, нарізка й фільтр доступу поруч | ports | Contributor | M | T5, T6 | todo |
| T8 | Перевірки етапу за таблицею покриття | tests | Contributor | M | T4, T5, T6, T7 | todo |
| T9 | DECISION.md — чекліст «RAG чи fine-tuning» | docs | Contributor | S | — | todo |
| T10 | Урок етапу: канон, міст на NovaShop, межі | docs | Contributor | M | T7, T8, T9 | todo |
| T11 | Вправи, еталонні розв'язки й чекліст | docs | Contributor | S | T10 | todo |
| T12 | Терміни етапу в глосарій, статус у програму | docs | Contributor | S | T10 | todo |

**Total:** 12 задач, ~8 людино-днів.

Паралельні гілки: T1, T2, T3 і T9 стартують одночасно. T5 і T6 — після T4.
T10 → T11 і T12 паралельно.
