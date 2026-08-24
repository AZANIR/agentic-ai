-- Таблиця фактів памʼяті. Приходить разом з етапом 6, якому вона потрібна.
--
-- До цього моменту факти жили у файлі JSONL (етап 5). Файл переживає перезапуск, якщо його
-- покласти на том, і НЕ переживає другого процесу: два одночасні записи втрачають дані.
-- Саме тому таблиця зʼявляється тут, а не «наперед, про всяк випадок».
--
-- Колонки повторюють `Fact` етапу 5 один в один. Це навмисно: сховище змінюється, запис — ні.

CREATE TABLE IF NOT EXISTS facts (
    id          BIGSERIAL PRIMARY KEY,
    owner       TEXT             NOT NULL,
    topic       TEXT             NOT NULL,
    text        TEXT             NOT NULL,
    stored_at   DOUBLE PRECISION NOT NULL,
    ttl         DOUBLE PRECISION,
    status      TEXT             NOT NULL DEFAULT 'active',
    replaced_at DOUBLE PRECISION,

    -- Ті самі правила, що у `from_line` етапу 5, але тепер їх тримає сховище.
    -- Запис зі статусом `replaced` без часу заміни валив `describe_skip` виключенням;
    -- у файлі це ловив парсер, тут ловить база — і ловить для всіх, хто пише.
    CONSTRAINT facts_status_known CHECK (status IN ('active', 'replaced')),
    CONSTRAINT facts_replaced_has_time CHECK (
        status <> 'replaced' OR replaced_at IS NOT NULL
    )
);

-- Вибірка завжди починається з власника: фільтр стоїть ДО відбору (ADR-0004 етапу 5).
-- В індексі він перший саме тому, а не за абеткою.
CREATE INDEX IF NOT EXISTS facts_owner_topic ON facts (owner, topic);

-- Активний факт тієї самої теми в одного власника може бути лише один. У файлі це
-- тримався код; тут — сховище, тобто правило переживе будь-якого нового автора запису.
CREATE UNIQUE INDEX IF NOT EXISTS facts_one_active_per_topic
    ON facts (owner, topic) WHERE status = 'active';
