PRAGMA foreign_keys = ON;

CREATE TABLE raw_market_events (
    row_id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    price REAL NOT NULL,
    volume INTEGER NOT NULL,
    currency TEXT NOT NULL,
    venue TEXT NOT NULL
);

CREATE TABLE symbol_aliases (
    source_symbol TEXT PRIMARY KEY,
    canonical_symbol TEXT NOT NULL
);

INSERT INTO symbol_aliases(source_symbol, canonical_symbol) VALUES
    ('AAA.US', 'AAA'),
    ('EEE.US', 'EEE');

CREATE VIEW normalized_events AS
SELECT
    r.row_id,
    UPPER(TRIM(r.source_system)) AS source_system,
    r.source_record_id,
    COALESCE(a.canonical_symbol, UPPER(TRIM(r.symbol))) AS symbol,
    r.event_time_utc,
    r.price,
    r.volume,
    UPPER(TRIM(r.currency)) AS currency,
    UPPER(TRIM(r.venue)) AS venue,
    COALESCE(a.canonical_symbol, UPPER(TRIM(r.symbol))) || '|' ||
        r.event_time_utc || '|' || UPPER(TRIM(r.venue)) AS event_key
FROM raw_market_events r
LEFT JOIN symbol_aliases a
    ON UPPER(TRIM(r.symbol)) = a.source_symbol;
