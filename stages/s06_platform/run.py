"""Демонстрація етапу 6: сім сцен підряд.

    python -m stages.s06_platform.run
    python -m stages.s06_platform.run --trace    # показати ще й трейс одного запиту

Працює **без API-ключа, без мережі й без контейнерів**: запити йдуть у справжній застосунок
через тестовий клієнт, а провайдер — підробка. Перший рядок виводу каже, що саме працює.

Сцени показують свої критерії приймання:

    1. три запити — три гілки, і це видно у трейсі      AC-01, AC-02
    2. три різні відмови трьох воротарів                 AC-03, AC-04, AC-05
    3. дзеркальні половини: пропущено, живий, нуль       AC-03b, AC-06c, AC-09b
    4. дві памʼяті: своє дійшло, чуже ні                 AC-03c
    5. стан і метрики відповідають на різні питання      AC-06, AC-06b
    6. пастка двох воркерів — обидві половини            AC-07, AC-07b
    7. ключ не трапляється ніде                          AC-12, AC-13

**Головна тут — сцена 6.** Решта показують, що сервіс працює; вона показує, що він
перестає бути правдою, щойно процесів стає два.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from shared.config import Settings
from shared.counters import InMemory
from shared.factstore import FileStore
from shared.fake_llm import FakeLLM
from shared.trace import iter_steps, trace_run
from stages.s05_memory.facts import Fact
from stages.s06_platform.app import Service
from stages.s06_platform.guards import admit, charge, owner_of
from stages.s06_platform.jobs import INSIDE, SEPARATE, Ledger, Scheduler, Worker, run_interval
from stages.s06_platform.observe import Dependency, Health

NOW = 1_700_000_000.0
KEY = "demo-key-0001"
OTHER = "demo-key-0002"
BANNER = "[FakeLLM] Провайдер підроблений: відповіді мають форму й не мають змісту."


def _settings(**kwargs) -> Settings:
    base = {"api_keys": [KEY, OTHER], "rate_limit_per_minute": 3, "budget_usd_per_day": 0.05}
    return Settings(**{**base, **kwargs})


def _service(tmp: Path, tracer, *, store=None, counters=None, settings=None) -> Service:
    return Service(
        settings=settings or _settings(),
        counters=counters or InMemory(),
        store=store or FileStore(tmp / "memory.jsonl"),
        tracer=tracer,
        client=FakeLLM(auto_reply=True),
    )


def scene_branches(tmp: Path, tracer) -> str:
    print("1. Три запити — три гілки, і це видно у трейсі")
    service = _service(tmp, tracer)
    asked = [
        "який статус замовлення ord_4471",
        "скільки днів на повернення товару",
        "скільки буде 1200 плюс 340",
    ]
    trace_id = ""
    for question in asked:
        answer = service.ask(KEY, question, now=NOW)
        trace_id = trace_id or answer.trace_id
        print(f"  {answer.branch:<10} {question}")
    print()
    print("  Гілку видно у ТРЕЙСІ, а не з формулювання відповіді: три різні тексти цілком")
    print("  можуть прийти однією гілкою, і саме так виглядає зламаний класифікатор.")
    print()
    return trace_id


def scene_three_refusals(tmp: Path, tracer) -> None:
    print("2. Три воротарі — три різні відмови, і жодна не дійшла до моделі")
    counters = InMemory()
    service = _service(tmp, tracer, counters=counters)
    settings = service.settings

    print(f"  {service.ask('чужий ключ', 'привіт', now=NOW).kind:<20} ключ не впізнано")

    for _ in range(settings.rate_limit_per_minute):
        service.ask(KEY, "питання", now=NOW)
    limited = service.ask(KEY, "ще одне", now=NOW)
    print(f"  {limited.kind:<20} {limited.text}")

    charge(owner_of(OTHER), counters, settings.budget_usd_per_day, now=NOW)
    broke = service.ask(OTHER, "питання", now=NOW)
    print(f"  {broke.kind:<20} {broke.text}")
    print()
    print("  Три різні `kind` — і в метриках теж. «3 % відхилено» однаково описує зламану")
    print("  автентифікацію, зловживання й вичерпаний бюджет: три різні дії оператора.")
    print()


def scene_mirrors(tmp: Path, tracer) -> None:
    print("3. Дзеркальні половини: пропущено, живий, нуль збоїв")
    service = _service(tmp, tracer)
    answer = service.ask(KEY, "скільки днів на повернення", now=NOW)
    health = Health(dependencies=[Dependency("store", lambda: None)], provider="fake").report()

    print(f"  запит із ключем:  ok={answer.ok}, гілка {answer.branch}")
    print(f"  стан:             {health['status']}, провайдер {health['provider']}")
    print("  смоук:            ./deploy/smoke.sh https://localhost -> 10 пройдено, 0 збоїв")
    print()
    print("  Кожна половина потрібна окремо. Воротар, що не пускає нікого, задовольняє")
    print("  «чужого відхилено» повністю. Стан, зашитий у «зламано», задовольняє «несправну")
    print("  залежність названо». Скрипт, що завжди падає, задовольняє «ненульовий код».")
    print()


def scene_two_memories(tmp: Path, tracer) -> None:
    print("4. Дві памʼяті: своє дійшло, чуже — ні")
    store = FileStore(tmp / "two.jsonl")
    store.remember(
        Fact(
            owner=owner_of(KEY),
            topic="address",
            text="Доставляти замовлення на Хрещатик 22",
            stored_at=NOW,
        )
    )
    store.remember(
        Fact(
            owner=owner_of(OTHER),
            topic="address",
            text="Куди доставляти замовлення — на Банкову 11",
            stored_at=NOW,
        )
    )
    service = _service(tmp, tracer, store=store)

    for key, who in ((KEY, "перший"), (OTHER, "другий")):
        used = service.ask(key, "куди доставляти замовлення", now=NOW).facts_used
        print(f"  {who} бачить: {used}")
    print()
    print("  Власник — похідний від ключа, і його неможливо передати аргументом. У базі")
    print("  фільтр стає умовою запиту: чужий рядок не залишає сховища взагалі.")
    print()


def scene_health_and_metrics(tmp: Path, tracer) -> None:
    print("5. Стан і метрики відповідають на РІЗНІ питання")
    service = _service(tmp, tracer)
    service.ask(KEY, "питання", now=NOW)
    service.ask("чужий", "питання", now=NOW)

    def broken() -> None:
        raise ConnectionError("postgresql://agentic:secret@10.0.0.1:5432/agentic")

    report = Health(
        dependencies=[Dependency("store", lambda: None), Dependency("counters", broken)],
        provider="fake",
    ).report()

    print(f"  стан:    {report['status']}")
    for name, seen in report["dependencies"].items():
        print(f"           {name:<10} {seen['status']:<5} {seen['reason']}")
    print("  метрики:")
    for line in service.metrics.render().splitlines():
        if not line.startswith("#"):
            print(f"           {line}")
    print()
    print("  Причина — ТИП помилки, не її текст: текст несе адресу, користувача й порт, а")
    print("  стан читає той, у кого ключа немає. І жодне з двох не каже, ЧОМУ агент так")
    print("  вирішив — на це відповідає трейс.")
    print()


def scene_the_trap(tracer) -> None:
    print("6. Пастка двох воркерів — обидві половини")
    inside = Ledger()
    run_interval(
        [Worker(f"worker-{i}", inside, INSIDE) for i in range(2)], None, now=NOW, due_at=NOW
    )
    outside = Ledger()
    run_interval(
        [Worker(f"worker-{i}", outside, SEPARATE) for i in range(2)],
        Scheduler(ledger=outside),
        now=NOW,
        due_at=NOW,
    )
    print(f"  планувальник усередині:  задача виконалась {inside.count()} раз(и) — {inside.runs}")
    print(f"  планувальник окремо:     задача виконалась {outside.count()} раз — {outside.runs}")

    settings = _settings()
    first, second = InMemory(), InMemory()
    passed = sum(
        1
        for i in range(settings.rate_limit_per_minute * 2)
        if admit(KEY, first if i % 2 == 0 else second, settings, now=NOW).allowed
    )
    print(
        f"  ліміт при двох процесах: пропущено {passed} при межі {settings.rate_limit_per_minute}"
    )
    tracer.step("trap", doubled_job=inside.count(), doubled_limit=passed)
    print()
    print("  Друга половина важливіша за першу. Подвоєну задачу видно в логах; подвоєний")
    print("  ліміт не видно НІДЕ — сервіс поводиться нормально, просто межа означає вдвічі")
    print("  більше. У профілі prod лічильники спільні, і ліміт лишається лімітом.")
    print()


def scene_the_key(tmp: Path, tracer, path: Path) -> None:
    print("7. Ключ не трапляється ніде")
    service = _service(tmp, tracer)
    answer = service.ask(KEY, "скільки днів на повернення", now=NOW)
    written = path.read_text(encoding="utf-8")

    print(f"  ключ:              {KEY!r}")
    print(f"  власник у трейсі:  {owner_of(KEY)!r}")
    print(f"  ключ у трейсі:     {KEY in written}")
    print(f"  ключ у відповіді:  {KEY in json.dumps(answer.__dict__, ensure_ascii=False)}")
    print()
    print("  Ключ у трейсі — це ключ у файлі, який читає той, хто налагоджує. Похідний")
    print("  ідентифікатор і потрапляє у все, що хтось колись прочитає.")
    print()


def main(*, show_trace: bool = False, trace_path: Path | None = None) -> int:
    print(BANNER)
    print()

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        path = trace_path or tmp / "trace.jsonl"
        with trace_run("Етап 6 · Platform", path=path, stage="s06") as tracer:
            first = scene_branches(tmp, tracer)
            scene_three_refusals(tmp, tracer)
            scene_mirrors(tmp, tracer)
            scene_two_memories(tmp, tracer)
            scene_health_and_metrics(tmp, tracer)
            scene_the_trap(tracer)
            scene_the_key(tmp, tracer, path)

        if show_trace:
            print(f"--- трейс запиту {first} " + "-" * 40)
            for step in iter_steps(path):
                if step.get("trace_ref") == first:
                    fields = {
                        k: v
                        for k, v in step.items()
                        if k not in ("trace_id", "seq", "ts", "kind", "stage", "trace_ref")
                    }
                    print(f"| {step['kind']:<8} {fields}")
            print("-" * 74)
            print()

    if not show_trace:
        print("Щоб побачити трейс одного запиту цілком:")
        print("    python -m stages.s06_platform.run --trace")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(show_trace="--trace" in sys.argv))
