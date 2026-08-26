# Do you need a supervisor here

The most common answer is **no**, and that is exactly why this checklist exists.

A graph of three agents looks like architecture, while one agent with three tools looks
unfinished. Systems in which every answer costs three model calls instead of one — and where a
routing mistake becomes a new class of incident — are built on that feeling.

## Three verdicts, not two

    ОДИН АГЕНТ     tools in one registry, one model call per answer
    КЛАСИФІКАТОР   a cheap branch choice with no revision loop
    SUPERVISOR     the full graph, with handoffs and revisions

**The middle verdict is the most important.** Most systems built as supervisors actually need
that one: the route is needed, the revision loop is not. The question "do we need a supervisor or
not" is posed wrongly precisely because between "no" and "yes" there is a third option, cheaper
than either extreme under its own conditions.

## The checklist

Rules are checked top to bottom and the first one to fire wins. The order is a decision too:

| Position | What we check | Why here |
|---|---|---|
| 1–3 | **Structural constraints** | No economy gets around them: if an answer has to be reviewed by another agent, there is no cheaper way |
| 4–5 | **Cost** | Latency and the price of a call are real, but they are negotiable |
| 6 | **Size** | The weakest argument, and the one heard most often |

| # | Signal | Answer |
|---|---|---|
| 1 | One agent's answer must be reviewed by another | **SUPERVISOR** |
| 2 | Different teams own different parts | **SUPERVISOR** |
| 3 | The parts need different models or settings | **SUPERVISOR** |
| 4 | The tool descriptions conflict with one another | **КЛАСИФІКАТОР** |
| 5 | Every extra handoff costs noticeable latency | **КЛАСИФІКАТОР** |
| 6 | There are more tools than the model holds in its head | **КЛАСИФІКАТОР** |
| — | No signal fired | **ОДИН АГЕНТ** |

The checklist does not exist only as text: the same rules sit in code in `decision.py`, and
checks assert that every situation has one answer **and that every rule has a situation**. Text
and code cannot drift apart unnoticed.

```
python -m stages.s03_router.decision
```

## Seven situations

| Ситуація | Відповідь | Чому |
|---|---|---|
| Юридичні відповіді має вичитувати другий агент | **SUPERVISOR** | Цикл ревізій — це і є supervisor. Один агент не перевіряє сам себе. |
| Платежі веде одна команда, каталог — інша | **SUPERVISOR** | Межа агентів має збігатися з межею відповідальності, інакше кожна зміна спільна. |
| Класифікації досить дешевої моделі, відповідям — ні | **SUPERVISOR** | Різні моделі неможливо тримати в одному реєстрі інструментів. |
| Модель плутає два схожі інструменти | **КЛАСИФІКАТОР** | Маршрут потрібен, цикл ревізій — ні. Це середина, яку зазвичай пропускають. |
| Голосовий асистент: пауза понад секунду чутна | **КЛАСИФІКАТОР** | Кожна передача — виклик моделі. Supervisor тут купується часом користувача. |
| Сорок інструментів в одному реєстрі | **КЛАСИФІКАТОР** | Вибір розмивається задовго до сорока. Групувати треба, розділяти агентів — ні. |
| П'ять інструментів, одна предметна область | **ОДИН АГЕНТ** | Найчастіший випадок і найчастіша помилка: граф там, де вистачає реєстру. |

## What the checklist does not decide

**It does not forbid starting with one agent and splitting later.** Quite the opposite: that is
the cheapest path, provided the boundary runs where you think it does. What is expensive is the
reverse — merging three agents into one after it turns out there was no boundary.

**It does not count money.** Every handoff is a model call; what that comes to per month depends
on traffic you do not know yet. You will have to do that arithmetic yourself, and in stage 6 a
budget guard appears for it.

**The last row of the table is the most important one.** Five tools in one domain need nothing
beyond stage 1's registry. That is the most common case and the most common mistake.
