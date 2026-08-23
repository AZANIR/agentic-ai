# Tracker — s03-router

> Стани: `todo` · `in_progress` · `blocked` · `review` · `done`.

| # | Task | Layer | Owner | Estimate | Blocked by | Status |
|---|---|---|---|---|---|---|
| T1 | Схема стану як оголошений контракт | domain | Contributor | S | — | todo |
| T2 | Три спеціалісти з описами компетенцій | domain | Contributor | S | T1 | todo |
| T3 | Граф: supervisor, маршрут, цикл ревізій | app | Contributor | S | T1, T2 | todo |
| T4 | Права доступу переживають передачу — три перевірки | tests | Contributor | S | T3 | todo |
| T5 | Чекліст «чи потрібен supervisor» кодом і прозою | domain | Contributor | S | — | todo |
| T6 | Та сама задача на LangGraph | infra | Contributor | S | T3 | todo |
| T7 | Демо: маршрути, ліміт, відмова, права | ports | Contributor | S | T3, T5 | todo |
| T8 | Перевірки до повного покриття таблиці | tests | Contributor | S | T3, T5, T6, T7 | todo |
| T9 | Урок українською й англійська карта | docs | Contributor | S | T7, T8 | todo |
| T10 | Вправи, розв'язки, чекліст | docs | Contributor | S | T8, T9 | todo |
| T11 | Глосарій і статуси | docs | Contributor | S | T9 | todo |
