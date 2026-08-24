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

from fastapi import Depends, FastAPI, Header, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from stages.s06_platform.guards import (
    BUDGET_EXHAUSTED,
    RATE_LIMITED,
    UNAUTHENTICATED,
    authenticate,
)
from stages.s06_platform.observe import UP

# Рід відмови -> код відповіді. Таблиця тут, а не в коді: домен про коди не знає, і додати
# новий рід має бути одним рядком, а не пошуком по гілках.
# Пʼятий рід результату: запит, який сервіс відхиляє за формою. Він має власне імʼя
# рівно тому, що решта чотири мають: «трафіку немає» й «клієнт шле сміття» — це різні
# дії оператора.
TOO_LONG = "malformed_request"

STATUS_OF = {
    UNAUTHENTICATED: 401,
    RATE_LIMITED: 429,
    BUDGET_EXHAUSTED: 402,
    TOO_LONG: 400,
    "dependency_down": 503,
}


class Ask(BaseModel):
    """Запит. Довжина перевіряється в обробнику, а не схемою.

    Схема з `max_length` давала 422 повз усе: без роду відмови, без кроку у трейсі,
    без метрики — і з **повним текстом запиту у відповіді про помилку**. Оператор
    бачив «трафіку немає», клієнт бачив постійні збої.

    Плюс межа була зашита числом, тоді як `MAX_MESSAGE_CHARS` існував у конфігурації
    й нічого не робив — операторська ручка, яка нічого не крутить.
    """

    question: str


def create_app(service: Any, health: Any) -> FastAPI:
    """Зібрати застосунок навколо готового сервісу. Нічого не створює сам — усе передано."""
    api = FastAPI(title="s06 platform", docs_url=None, redoc_url=None)

    def key_of(x_api_key: str = Header(default="")) -> str:
        return x_api_key

    @api.post("/ask")
    def ask(body: Ask, key: str = Depends(key_of)) -> JSONResponse:
        limit = service.settings.max_message_chars
        if not body.question.strip() or len(body.question) > limit:
            service.metrics.request(TOO_LONG)
            return JSONResponse(
                {
                    "ok": False,
                    "kind": TOO_LONG,
                    "text": f"запит має бути від 1 до {limit} символів",
                },
                status_code=STATUS_OF[TOO_LONG],
            )
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
    def metrics(key: str = Depends(key_of)) -> Response:
        """З ключем навмисно: агрегати теж розкривають.

        Невдала спроба **рахується**. Донедавна вона проходила повз усе: не
        інкрементувала ліміт, не потрапляла в метрики, не лишала кроку у трейсі —
        тобто перебір ключа по цьому ендпоінту був невидимий для всіх трьох
        механізмів спостережуваності етапу.
        """
        verdict = authenticate(key, service.settings)
        if not verdict.allowed:
            service.metrics.request(verdict.kind)
            return PlainTextResponse("", status_code=401)
        return PlainTextResponse(service.metrics.render(), media_type="text/plain")

    return api
