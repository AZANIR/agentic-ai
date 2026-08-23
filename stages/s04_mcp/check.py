"""Перевірки етапу 4.

    python -m stages.s04_mcp.check

Офлайн, без ключа. Частина перевірок потребує **справжнього сервера в підпроцесі** — без
встановленого пакета MCP вони позначаються `НЕ ПЕРЕВІРЕНО`, а не проходять: різниця між
«збіглося» і «не перевіряли» має лишатись видимою (урок етапу 3).

Розбір відповіді перевіряється **без сервера** навмисно. Це половина уроку етапу, і вимагати
для неї підпроцесу означало б зробити найважливіші перевірки найповільнішими.
"""

from __future__ import annotations

from shared.check_runner import run_checks
from stages.s04_mcp.parse import NoPayload, describe_failure, extract_payload

# Реальна форма відповіді MCP-сервера, який любить поговорити. Проза до, проза після.
CHATTY = """Ось що я знайшов у системі замовлень. Зверніть увагу, що дані актуальні
на момент запиту й можуть змінитися.

```json
{"order_id": "ord_4471", "status": "in_transit", "eta_days": 2}
```

Якщо потрібна історія змін, скористайтеся окремим інструментом.
"""

CLEAN = '{"order_id": "ord_4471", "status": "in_transit", "eta_days": 2}'

PROSE_ONLY = """На жаль, я не зміг обробити цей запит: система замовлень не відповідає.
Спробуйте пізніше або зверніться до підтримки.
"""

EMPTY_LIST = """Пошук виконано.

```json
[]
```
"""


def check_payload_survives_prose_around_it() -> None:
    """ВІДМОВА · parse: дані дістаються з відповіді, обгорнутої прозою"""
    payload = extract_payload(CHATTY)
    assert payload == {"order_id": "ord_4471", "status": "in_transit", "eta_days": 2}, payload


def check_a_clean_response_still_parses() -> None:
    """parse: відповідь без прози розбирається тим самим кодом"""
    assert extract_payload(CLEAN)["order_id"] == "ord_4471"


def check_no_payload_is_named_not_guessed() -> None:
    """ВІДМОВА · parse: відсутність даних — окремий стан, не порожній результат"""
    try:
        extract_payload(PROSE_ONLY)
    except NoPayload as error:
        assert "не відповідає" in str(error) or "система замовлень" in str(error), (
            "повідомлення має нести текст сервера — інакше діагностувати нічим"
        )
    else:
        raise AssertionError(
            "проза без даних розібралась — «сервер нічого не повернув» злилось із "
            "«сервер повернув порожнє»"
        )


def check_an_empty_result_is_not_a_missing_one() -> None:
    """ВІДМОВА · parse: порожній перелік — це результат, а не відсутність даних"""
    payload = extract_payload(EMPTY_LIST)
    assert payload == [], payload


def check_prose_that_merely_looks_like_data_is_not_taken() -> None:
    """ВІДМОВА · parse: приклад у прозі не приймається за дані"""
    tricky = """Формат відповіді такий: {"order_id": "...", "status": "..."} — але
зараз даних немає, бо замовлення не знайдено.
"""
    try:
        extract_payload(tricky)
    except NoPayload:
        pass
    else:
        raise AssertionError(
            "приклад із пояснення взято за дані — так парсер одного дня поверне "
            "фрагмент документації замість відповіді"
        )


def check_failure_description_names_the_phase() -> None:
    """parse: опис відмови називає фазу, а не лише текст винятку"""
    described = describe_failure(NoPayload("сервер нічого не повернув"), phase="parse")
    assert described["phase"] == "parse", described
    assert "нічого не повернув" in described["reason"]
    assert set(described) == {"phase", "reason"}, described


CHECKS = [
    check_payload_survives_prose_around_it,
    check_a_clean_response_still_parses,
    check_no_payload_is_named_not_guessed,
    check_an_empty_result_is_not_a_missing_one,
    check_prose_that_merely_looks_like_data_is_not_taken,
    check_failure_description_names_the_phase,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 4 · MCP")


if __name__ == "__main__":
    raise SystemExit(main())
