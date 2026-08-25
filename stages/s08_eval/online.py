"""Онлайн-оцінювання: дешеві чеки на всьому, суддя на частці (ADR-0007).

**Поза смугою, а не в гарячому шляху.** Жоден крок оцінювання не стоїть між запитом і
відповіддю — усе читається з трейсу **після**. Сервіс, чию затримку етап 7 щойно міряв цілим
етапом, не отримує невиміряного доданка.

Ціна названа прямо: запит, який до трейсера не дійшов, не оцінюється **ніяк**. Інлайнові
чеки зловили б і його — за рахунок затримки на кожному запиті.

**Відбір детермінований**, за хешем ідентифікатора запиту. Випадкове число проти порога
зробило б перевірку мигтливою, а допуск довелося б розширити настільки, що він перестав би
розрізняти десять відсотків і один. Той самий потік ідентифікаторів завжди дає ту саму
частку, і її можна звірити із заявленою.

Межа звірки — **±3 відсоткові пункти на потоці від двохсот** — стоїть у специфікації, а не
обирається цим модулем. Харнес, що сам оголошує свою межу, завжди правий.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from stages.s08_eval.judge import Judge, Unavailable
from stages.s08_eval.levels import BROKEN_KINDS
from stages.s08_eval.trajectory import Key, Trajectory, by_ref, extract

DEFAULT_SHARE = 0.10
TOLERANCE = 0.03
MIN_STREAM = 200

# Роздільна здатність хешу. Десять тисяч кошиків дають крок 0.01 відсоткового пункта —
# дрібніше за будь-яку частку, яку має сенс оголошувати.
BUCKETS = 10_000


def sampled(request_id: str, *, share: float = DEFAULT_SHARE) -> bool:
    """Чи йде цей запит до судді. Чиста функція ідентифікатора й частки."""
    digest = hashlib.blake2b(request_id.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % BUCKETS < share * BUCKETS


@dataclass
class Watch:
    """Що дав прохід по трафіку. Тексту запиту тут немає — лише рішення й числа."""

    checked: int = 0
    # Скільки ВІДІБРАНО в семпл і скільки суддя встиг оцінити — різні числа, і плутати їх
    # означає приписувати семплерові відмову приладу. Частка міряє перше.
    sampled_count: int = 0
    judged: int = 0
    unscored: int = 0
    problems: list[str] = field(default_factory=list)
    # Виміри, яких цей трейс не підтримує. Не «зауважень нуль», а «дивитись нема на що»:
    # третій стан діє й тут. Саме цей перелік і є виміряною відповіддю на питання, чого
    # оцінювачеві бракує у трейсах (ADR-0008).
    blind: list[str] = field(default_factory=list)

    @property
    def share(self) -> float:
        """Частка **відібраних**, а не оцінених.

        Рахувати від `judged` означало б, що вичерпана квота судді робить семплер
        неправильним: та сама плутанина «скільки відібрали» / «скільки прилад відповів»,
        проти якої написаний цей етап.
        """
        return self.sampled_count / self.checked if self.checked else 0.0

    def within(self, target: float = DEFAULT_SHARE) -> bool:
        """Чи збіглася фактична частка із заявленою. На короткому потоці — не питання."""
        return self.checked < MIN_STREAM or abs(self.share - target) <= TOLERANCE

    def line(self, target: float = DEFAULT_SHARE) -> str:
        blind = f", сліпих вимірів {len(self.blind)}" if self.blind else ""
        return (
            f"перевірено {self.checked}, у семплі {self.sampled_count} "
            f"({self.share:.1%} проти заявлених {target:.0%}), "
            f"оцінено {self.judged}, не оцінено {self.unscored}, "
            f"зауважень {len(self.problems)}{blind}"
        )


def blind_spots(trajectories: list[Trajectory]) -> list[str]:
    """Чого цей трейс не дає перевірити — виміряно, а не припущено.

    На трейсах сервісу етапу 6 сюди потрапляють обидва пункти: ані відповіді, ані
    термінального кроку запиту там немає. «Зауважень нуль» на такому файлі означало б
    «усе гаразд» замість «дивитись нема на що».
    """
    missing = []
    if not any(trajectory.answer() for trajectory in trajectories):
        missing.append("відповідей у трейсі немає — порожню відповідь не спіймати")
    if not any(trajectory.outcome() for trajectory in trajectories):
        missing.append("термінального кроку немає — незавершений прогін не спіймати")
    return missing


def cheap(trajectory: Trajectory, *, blind: list[str] | None = None) -> list[str]:
    """Детерміновані чеки на **кожній** траєкторії. Ані виклику моделі, ані тексту запиту."""
    blind = blind or []
    found = []
    # `length` виключає обрамлення. `not steps` не настає на жодному справжньому трейсі:
    # `trace_run` завжди пише `run_start` і `run_end`, тож умова була недосяжною.
    if trajectory.length == 0:
        found.append("порожня траєкторія")
    if any(step["kind"] in BROKEN_KINDS for step in trajectory.steps):
        broken = next(s["kind"] for s in trajectory.steps if s["kind"] in BROKEN_KINDS)
        found.append(f"відмова підсистеми: {broken}")
    # Чек порожньої відповіді. Він мусить існувати: `blind_spots` оголошує сліпоту саме
    # до нього, а сліпота до перевірки, якої немає, — це порожня обіцянка. Під тим самим
    # охоронцем, бо на трейсі без відповідей вона нічого не значить.
    if (
        not any(spot.startswith("відповідей") for spot in blind)
        and not (trajectory.answer() or "").strip()
    ):
        found.append("порожня відповідь")
    if not any(spot.startswith("термінального") for spot in blind):
        if trajectory.outcome() is None:
            found.append("прогін не завершився")
        elif trajectory.outcome() != "ok":
            found.append(f"прогін завершився як {trajectory.outcome()}")
    return found


def watch(
    path: Path | str,
    *,
    key: Key = by_ref,
    judge: Judge | None = None,
    share: float = DEFAULT_SHARE,
    task: str = "запит користувача",
) -> Watch:
    """Пройти трафік із трейсу: дешеві чеки на всьому, суддя — на частці.

    `task` — стала підпис, а не текст **запиту**: судді досить знати, що це запит
    користувача, а матеріали оцінювання не мають нести написаного людиною (AC-07b).

    **Ціна названа прямо, а не замовчана.** Судити відповідь, не показавши її судді,
    неможливо, тож `trajectory.answer()` до нього доходить — а з `--real` доходить і до
    провайдера. Заборона AC-07b стосується **матеріалів оцінювання**: записаного звіту й
    власного трейсу прогону. У них не лишається ані запиту, ані відповіді — лише рішення
    й числа. Хто цього не хоче, вимикає суддю: дешеві чеки працюють без нього.
    """
    walked = extract(path, key=key)
    seen = Watch(blind=blind_spots(walked))
    for trajectory in walked:
        seen.checked += 1
        # Ідентифікатор траєкторії, а не її зміст: у семпл потрапляє запит, а не текст.
        for problem in cheap(trajectory, blind=seen.blind):
            seen.problems.append(f"{trajectory.key}: {problem}")
        if not sampled(trajectory.key, share=share):
            continue
        seen.sampled_count += 1
        if judge is None:
            continue
        try:
            judge.score(task, trajectory.answer() or "", "")
            seen.judged += 1
        except Unavailable:
            seen.unscored += 1
    return seen
