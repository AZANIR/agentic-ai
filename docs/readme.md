# Джерела курсу

Курс побудований за серією **«Agentic AI: From Zero to Production»** Sai Bhargav Rallapalli.

> **Повних текстів статей тут немає — і це навмисно.** Статті належать їхньому авторові;
> дзеркалити їх у публічному репозиторії було б неправильно. Нижче — посилання на оригінали
> та **власні конспекти своїми словами**: рівно стільки, щоб зрозуміти, звідки взялася ідея
> кожного етапу, не читаючи оригінал.
>
> Етапи курсу й так **не копіюють** текст статей: вони переказують ідеї і будують за ними
> працюючий код. Тож курс повністю самодостатній — оригінали читати корисно, але не обов'язково.

Автор серії: [Sai Bhargav Rallapalli](https://saibhargavr.medium.com/) ·
[LinkedIn](https://linkedin.com/in/sai-bhargav-rallapalli)

---

### 1. [What is an AI Agent? The Simplest Explanation You’ll Find](https://blog.gopenai.com/what-is-an-ai-agent-the-simplest-explanation-youll-find-e7b176a31c44)

Агент — це мовна модель, яка може **діяти**. Три складові (мозок, інструменти, пам'ять), цикл Plan→Act→Observe→Decide і три способи, якими це ламається: нескінченний цикл, вигадані аргументи, незворотна дія «на всяк випадок».

**Етап курсу:** [`stages/s01_agent_loop/`](../stages/s01_agent_loop/) · **Читання оригіналу:** ~6 хв

---

### 2. [RAG vs Fine-Tuning: Which One Actually Solves Your Problem?](https://blog.gopenai.com/rag-vs-fine-tuning-which-one-actually-solves-your-problem-06df08b5dc40)

RAG змінює те, що модель **знає**; fine-tuning — те, як вона **поводиться**. Дерево рішень із шести питань: змінні дані й потреба цитувати джерела ведуть до RAG, стабільна вузька задача великого обсягу — до fine-tuning.

**Етап курсу:** [`stages/s02_rag/`](../stages/s02_rag/) · **Читання оригіналу:** ~5 хв

---

### 3. [Build a Multi-Agent Router with LangGraph in 30 Minutes](https://blog.gopenai.com/build-a-multi-agent-router-with-langgraph-in-30-minutes-8ee979116b53)

Один роздутий агент програє трьом вузьким. Supervisor — це той самий агент, у якого інструментами є інші агенти. Дві реальні пастки: схема стану, яку найдорожче міняти пізніше, і нескінченний цикл ревізій.

**Етап курсу:** [`stages/s03_router/`](../stages/s03_router/) · **Читання оригіналу:** ~7 хв

---

### 4. [MCP Protocol Explained: The New Standard Every AI Developer Needs to Know](https://blog.gopenai.com/mcp-protocol-explained-the-new-standard-every-ai-developer-needs-to-know-0e3e56aee2aa)

MCP робить для інструментів агента те, що USB зробив для периферії: один протокол замість інтеграції під кожен сервіс. Host / client / server, tools / resources / prompts, і перехід специфікації до stateless.

**Етап курсу:** [`stages/s04_mcp/`](../stages/s04_mcp/) · **Читання оригіналу:** ~7 хв

---

### 5. [Memory in AI Agents: Why Your Agent Forgets Everything (And How to Fix It)](https://blog.gopenai.com/memory-in-ai-agents-why-your-agent-forgets-everything-and-how-to-fix-it-250150317ff1)

Пам'ять — не властивість моделі, а система навколо неї: extract → store → retrieve. Головна пастка — «зберігати все»: контекст роздувається, вартість росте, а якість падає (context rot).

**Етап курсу:** [`stages/s05_memory/`](../stages/s05_memory/) · **Читання оригіналу:** ~6 хв

---

### 6. [I Built a Multi-Connector AI Platform on a Single VM — Here’s the Real Architecture](https://blog.gopenai.com/i-built-a-multi-connector-ai-platform-on-a-single-vm-heres-the-real-architecture-656c9c3f3044)

Як п'ять попередніх ідей стають одним працюючим сервісом на одній VM. Класифікатор замість повного supervisor там, де домени не перетинаються; нудна інфраструктура навмисне; пастка планувальника при кількох воркерах.

**Етап курсу:** [`stages/s06_platform/`](../stages/s06_platform/) · **Читання оригіналу:** ~7 хв

---

### 7. [Voice Agents at Scale: What Breaks When Millions of People Talk to Your AI](https://blog.gopenai.com/voice-agents-at-scale-what-breaks-when-millions-of-people-talk-to-your-ai-87750cc78054)

Голос — не «текст, але швидше». Бюджет ~600 мс на весь конвеєр змушує стрімити кожну стадію, а barge-in (перебивання) — окрема задача, якої в текстових агентів не існує взагалі.

**Етап курсу:** [`stages/s07_voice/`](../stages/s07_voice/) · **Читання оригіналу:** ~7 хв

---

### 8. [Agent Evaluation: How Do You Know Your Agent Actually Works?](https://blog.gopenai.com/agent-evaluation-how-do-you-know-your-agent-actually-works-1c6b7cef5461)

Агент може викликати всі інструменти правильно й усе одно провалити задачу — або наплутати й випадково вгадати. Тому оцінювати треба **шлях**, а не лише останнє повідомлення. Три рівні й чотири біаси судді-LLM.

**Етап курсу:** [`stages/s08_eval/`](../stages/s08_eval/) · **Читання оригіналу:** ~7 хв

---

### 9. [LangGraph vs CrewAI vs Google ADK: I Built the Same Agent Three Times](https://blog.gopenai.com/langgraph-vs-crewai-vs-google-adk-i-built-the-same-agent-three-times-87c2f2ce3b59)

Один і той самий двоагентний таск, написаний тричі. LangGraph дає контроль, CrewAI — швидкість до прототипу, ADK — інтеграцію з Google Cloud і A2A. Фреймворк — це риштування, а не архітектура.

**Етап курсу:** [`stages/s09_frameworks/`](../stages/s09_frameworks/) · **Читання оригіналу:** ~7 хв

---

### 10. [The Capstone: Building One Real Agent With Everything From This Series](https://blog.gopenai.com/the-capstone-building-one-real-agent-with-everything-from-this-series-23742b41fcc7)

Складання всього в один support-агент для інтернет-магазину. Головна теза серії: цінність не в десяти темах, а в умінні робити ті самі компроміси в системі, про яку туторіалу ще ніхто не написав.

**Етап курсу:** [`stages/s10_capstone/`](../stages/s10_capstone/) · **Читання оригіналу:** ~7 хв

---

## Якщо хочеш читати оригінали локально

Скачай статті у цю теку під іменами `01-*.md` … `10-*.md`. Вони внесені до `.gitignore`,
тож у git не потраплять і випадково не опиняться в публічному репозиторії.
