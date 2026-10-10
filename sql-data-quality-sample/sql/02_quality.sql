CREATE VIEW quality_flags AS
WITH ranked AS (
    SELECT
        n.*,
        ROW_NUMBER() OVER (
            PARTITION BY event_key
            ORDER BY row_id
        ) AS duplicate_rank
    FROM normalized_events n
)
SELECT
    row_id,
    CASE
        WHEN event_time_utc NOT GLOB '????-??-??T??:??:??Z'
            OR strftime(
                '%Y-%m-%dT%H:%M:%SZ',
                julianday(event_time_utc)
            ) IS NOT event_time_utc THEN 'invalid_timestamp'
        WHEN typeof(price) NOT IN ('integer', 'real') THEN 'invalid_price_type'
        -- SQLite REAL uses IEEE-754 binary64; this is its finite maximum, not a sample price cap.
        WHEN price > 1.7976931348623157e308
            OR price < -1.7976931348623157e308 THEN 'non_finite_price'
        WHEN price <= 0 THEN 'non_positive_price'
        WHEN volume < 0 THEN 'negative_volume'
        WHEN currency NOT GLOB '[A-Z][A-Z][A-Z]' THEN 'invalid_currency'
        WHEN duplicate_rank > 1 THEN 'duplicate_normalized_event'
        ELSE NULL
    END AS quality_issue
FROM ranked;

CREATE VIEW accepted_events AS
SELECT n.*
FROM normalized_events n
JOIN quality_flags q USING (row_id)
WHERE q.quality_issue IS NULL;

CREATE VIEW quarantine_events AS
SELECT n.*, q.quality_issue
FROM normalized_events n
JOIN quality_flags q USING (row_id)
WHERE q.quality_issue IS NOT NULL;
