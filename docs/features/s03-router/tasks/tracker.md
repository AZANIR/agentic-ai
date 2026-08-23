# Tracker — s03-router

> Стани: `todo` · `in_progress` · `blocked` · `review` · `done`.

| # | Task | Layer | Owner | Estimate | Blocked by | Status |
|---|---|---|---|---|---|---|
| T1 | Схема стану як оголошений контракт | domain | Contributor | S | — | done |
| T2 | Три спеціалісти з описами компетенцій | domain | Contributor | S | T1 | done |
| T3 | Граф: supervisor, маршрут, цикл ревізій | app | Contributor | S | T1, T2 | done |
| T4 | Права доступу переживають передачу — три перевірки | tests | Contributor | S | T3 | done |
| T5 | Чекліст «чи потрібен supervisor» кодом і прозою | domain | Contributor | S | — | done |
| T6 | Та сама задача на LangGraph | infra | Contributor | S | T3 | done |
| T7 | Демо: маршрути, ліміт, відмова, права | ports | Contributor | S | T3, T5 | done |
| T8 | Перевірки до повного покриття таблиці | tests | Contributor | S | T3, T5, T6, T7 | done |
| T9 | Урок українською й англійська карта | docs | Contributor | S | T7, T8 | done |
| T10 | Вправи, розв'язки, чекліст | docs | Contributor | S | T8, T9 | done |
| T11 | Глосарій і статуси | docs | Contributor | S | T9 | done |
