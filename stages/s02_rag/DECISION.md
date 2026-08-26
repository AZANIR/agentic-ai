# RAG, fine-tuning, or just a prompt

The question "RAG or fine-tuning" is almost always posed wrongly, because these are not two ways
of doing the same thing.

    RAG           adds FACTS the model does not know
    fine-tuning   changes BEHAVIOUR: format, tone, way of reasoning
    a prompt      does both — while the material fits in the context window

The question "which is better" has no answer. The question "what facts do we have and whose
behaviour is this" does, and almost always an unambiguous one.

## The checklist

Rules are checked top to bottom and the first one to fire wins. The order is not accidental:
signals about **facts** sit above signals about **form**, because confusing them is expensive in
one direction and cheap in the other. Fine-tuning a model that was actually short of fresh data
is weeks of work and the same wrong answer at the end of it. Standing up RAG where fine-tuning
was needed is wasted infrastructure, and you see that within a day.

| # | Signal | Answer | Why |
|---|---|---|---|
| 1 | The data changes faster than you can retrain | **RAG** | Fine-tuning freezes the state as of training day and goes quietly stale — with no error in the output |
| 2 | Every answer must have an openable document under it | **RAG** | A model cannot cite a document it never saw while answering |
| 3 | Different people must see different things from the same sources | **RAG** | A fine-tuned model cannot forget part of itself for one interlocutor |
| 4 | There is more material than fits in the context window | **RAG** | Picking what a specific question needs is exactly what retrieval is |
| 5 | You need a fixed format or tone, not new facts | **ДОНАВЧАННЯ** | Retrieval does not change **how** the model speaks |
| 6 | The model does not speak the language of the domain | **ДОНАВЧАННЯ** | This is not a shortage of facts but a shortage of vocabulary |
| — | No signal fired | **ПРОСТО ПРОМПТ** | The cheapest solution, and the one skipped most often |

The checklist does not exist only as text: `decision.py` holds the same rules in code, and checks
assert that for each of the seven situations below it gives exactly one answer. Text and code
cannot drift apart unnoticed.

```
python -m stages.s02_rag.decision
```

## Seven situations

| Ситуація | Відповідь | Чому |
|---|---|---|
| Політику повернень переписують щокварталу | **RAG** | Донавчання зафіксує стан на день навчання й тихо застаріє. |
| Юристи вимагають посилання під кожною відповіддю | **RAG** | Модель не може послатися на документ, якого не бачила під час відповіді. |
| Оператори бачать внутрішні пороги, покупці — ні | **RAG** | Донавчена модель не вміє забути частину себе для одного співрозмовника. |
| Дванадцять тисяч сторінок документації | **RAG** | У вікно контексту не влізе; вибирати потрібне під питання — це і є пошук. |
| Відповідь завжди має бути в тому самому суворому форматі | **ДОНАВЧАННЯ** | Це поведінка, а не факт. Пошук не змінює того, як модель говорить. |
| Модель не знає внутрішнього жаргону компанії | **ДОНАВЧАННЯ** | Це не брак фактів, а брак словника. Пошук не вчить моделі говорити. |
| Вісім сторінок правил, які не мінялися два роки | **ПРОСТО ПРОМПТ** | Усе влізе в промпт. RAG тут — інфраструктура заради інфраструктури. |

## What the checklist does not decide

**It does not say "do not do both".** A model fine-tuned on your format sitting on top of RAG is
a normal and common construction: retrieval supplies the facts, fine-tuning supplies the form.
The checklist says where to start, not what is forbidden.

**It does not count money.** RAG costs infrastructure and latency on every request; fine-tuning
costs once, a lot, and once more each time the data changes. Which of the two is cheaper depends
on how many requests you have and how often the data moves. You will have to do that arithmetic
yourself.

**The last row of the table is the most important one.** Eight pages of rules that have not
changed in two years fit into a prompt whole. RAG over them is an index, an embedder, a
threshold and a filter for material you could simply have pasted in. The cheapest solution is
skipped most often precisely because it does not look like a solution.
