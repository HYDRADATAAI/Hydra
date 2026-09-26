CREATE VIEW symbol_activity_summary AS
WITH sequenced AS (
    SELECT
        symbol,
        event_time_utc,
        price,
        volume,
        LAG(price) OVER (
            PARTITION BY symbol
            ORDER BY event_time_utc
        ) AS previous_price,
        AVG(volume) OVER (
            PARTITION BY symbol
        ) AS avg_symbol_volume
    FROM accepted_events
)
SELECT
    symbol,
    COUNT(*) AS accepted_rows,
    ROUND(MIN(price), 2) AS min_price,
    ROUND(MAX(price), 2) AS max_price,
    SUM(volume) AS total_volume,
    ROUND(AVG(avg_symbol_volume), 2) AS avg_symbol_volume,
    ROUND(MAX(
        CASE
            WHEN previous_price IS NULL OR previous_price = 0 THEN 0
            ELSE ((price - previous_price) / previous_price) * 100.0
        END
    ), 4) AS max_step_return_pct
FROM sequenced
GROUP BY symbol;

CREATE VIEW quality_summary AS
SELECT
    COALESCE(quality_issue, 'accepted') AS outcome,
    COUNT(*) AS row_count
FROM quality_flags
GROUP BY quality_issue;
