"""HTTP-поверхня: три маршрути й нічого більше.

Окремо від `app.py` навмисно, і не заради чистоти. `Service` має перевірятись **без**
установленого веб-фреймворка: інакше весь набір етапу вимагає `pip install -e ".[s06]"`, і
правило курсу «усе працює на базовій установці» перестає діяти рівно там, де етап найбільший.

Тут немає жодного рішення. Усі три — у `guards.py`, `app.py` і `observe.py`; цей файл лише
перекладає їх у відповіді. Модуль, у якому зʼявиться `if`, що вирішує щось про домен, треба
читати як сигнал, що межа зʼїхала.

**Стан відкритий, метрики закриті** (AC-13). Стан читає зовнішній монітор, у якого ключа
немає й не має бути. Метрики закриті, бо кількість запитів на клієнта — бізнес-інформація.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from stages.s06_platform.guards import (
    BUDGET_EXHAUSTED,
    RATE_LIMITED,
    UNAUTHENTICATED,
    authenticate,
)
from stages.s06_platform.observe import UP

# Рід відмови -> код відповіді. Таблиця тут, а не в коді: домен про коди не знає, і додати
# новий рід має бути одним рядком, а не пошуком по гілках.
STATUS_OF = {
    UNAUTHENTICATED: 401,
    RATE_LIMITED: 429,
    BUDGET_EXHAUSTED: 402,
    "dependency_down": 503,
}


class Ask(BaseModel):
    """Запит. Довжина обмежена: недовірений вхід не має права бути будь-яким."""

    question: str = Field(min_length=1, max_length=4000)


def create_app(service: Any, health: Any) -> FastAPI:
    """Зібрати застосунок навколо готового сервісу. Нічого не створює сам — усе передано."""
    api = FastAPI(title="s06 platform", docs_url=None, redoc_url=None)

    def key_of(x_api_key: str = Header(default="")) -> str:
        return x_api_key

    @api.post("/ask")
    def ask(body: Ask, key: str = Depends(key_of)) -> JSONResponse:
        answer = service.ask(key, body.question)
        payload: dict[str, Any] = {
            "ok": answer.ok,
            "text": answer.text,
            "trace_id": answer.trace_id,
        }
        if answer.ok:
            payload["branch"] = answer.branch
            return JSONResponse(payload)

        payload["kind"] = answer.kind
        headers = {}
        if answer.retry_after is not None:
            headers["Retry-After"] = str(int(answer.retry_after))
        return JSONResponse(payload, status_code=STATUS_OF.get(answer.kind, 500), headers=headers)

    @api.get("/healthz")
    def healthz() -> JSONResponse:
        """Без ключа навмисно: монітор його не має. І нічого чутливого — лише імена й стан."""
        report = health.report()
        return JSONResponse(report, status_code=200 if report["status"] == UP else 503)

    @api.get("/metrics")
    def metrics(request: Request, key: str = Depends(key_of)) -> Response:
        """З ключем навмисно: агрегати теж розкривають."""
        if not authenticate(key, service.settings).allowed:
            return PlainTextResponse("", status_code=401)
        return PlainTextResponse(service.metrics.render(), media_type="text/plain")

    return api
