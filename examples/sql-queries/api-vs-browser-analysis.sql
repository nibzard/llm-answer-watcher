-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- API vs Browser Divergence Analysis Queries
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
--
-- These SQL queries help analyze divergence between API and browser responses.
-- Use these to generate statistics for research reports and marketing materials.
--
-- Usage:
--   sqlite3 llm_answers.db < examples/sql-queries/api-vs-browser-analysis.sql
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- ============================================================================
-- 1. Find Paired Responses (Same Intent, Different Runner Type)
-- ============================================================================

SELECT
    r.run_id,
    r.timestamp_utc as run_date,
    ar1.intent_id,
    ar1.model_provider,

    -- API response
    ar1.model_name as api_model,
    LENGTH(ar1.answer_text) as api_length,
    ar1.estimated_cost_usd as api_cost,

    -- Browser response
    ar2.runner_name as browser_runner,
    LENGTH(ar2.answer_text) as browser_length,
    ar2.screenshot_path,

    -- Quick divergence indicator (simplified)
    CASE
        WHEN ar1.answer_text = ar2.answer_text THEN 'IDENTICAL'
        WHEN LENGTH(ar1.answer_text) != LENGTH(ar2.answer_text) THEN 'LENGTH_DIFF'
        ELSE 'CONTENT_DIFF'
    END as divergence_indicator

FROM runs r
INNER JOIN answers_raw ar1 ON
    r.run_id = ar1.run_id
    AND ar1.runner_type = 'api'
INNER JOIN answers_raw ar2 ON
    r.run_id = ar2.run_id
    AND ar1.intent_id = ar2.intent_id
    AND ar2.runner_type = 'browser'
ORDER BY r.timestamp_utc DESC, ar1.intent_id;

-- ============================================================================
-- 2. Brand Mention Divergence (Brands in API but not Browser, or vice versa)
-- ============================================================================

-- Brands unique to API (appear in API but NOT in Browser)
SELECT
    m1.run_id,
    m1.intent_id,
    m1.model_provider,
    m1.normalized_name as brand,
    m1.rank_position as api_rank,
    'API_ONLY' as divergence_type
FROM mentions m1
WHERE m1.run_id || m1.intent_id || m1.normalized_name NOT IN (
    -- Subquery: All brands that appear in Browser for this (run_id, intent_id)
    SELECT
        m2.run_id || m2.intent_id || m2.normalized_name
    FROM mentions m2
    INNER JOIN answers_raw ar ON
        m2.run_id = ar.run_id
        AND m2.intent_id = ar.intent_id
        AND m2.model_provider = ar.model_provider
        AND m2.model_name = ar.model_name
    WHERE ar.runner_type = 'browser'
)
AND EXISTS (
    -- Ensure this is from an API runner
    SELECT 1 FROM answers_raw ar
    WHERE ar.run_id = m1.run_id
        AND ar.intent_id = m1.intent_id
        AND ar.model_provider = m1.model_provider
        AND ar.model_name = m1.model_name
        AND ar.runner_type = 'api'
)

UNION ALL

-- Brands unique to Browser (appear in Browser but NOT in API)
SELECT
    m1.run_id,
    m1.intent_id,
    m1.model_provider,
    m1.normalized_name as brand,
    m1.rank_position as browser_rank,
    'BROWSER_ONLY' as divergence_type
FROM mentions m1
WHERE m1.run_id || m1.intent_id || m1.normalized_name NOT IN (
    -- Subquery: All brands that appear in API for this (run_id, intent_id)
    SELECT
        m2.run_id || m2.intent_id || m2.normalized_name
    FROM mentions m2
    INNER JOIN answers_raw ar ON
        m2.run_id = ar.run_id
        AND m2.intent_id = ar.intent_id
        AND m2.model_provider = ar.model_provider
        AND m2.model_name = ar.model_name
    WHERE ar.runner_type = 'api'
)
AND EXISTS (
    -- Ensure this is from a Browser runner
    SELECT 1 FROM answers_raw ar
    WHERE ar.run_id = m1.run_id
        AND ar.intent_id = m1.intent_id
        AND ar.model_provider = m1.model_provider
        AND ar.model_name = m1.model_name
        AND ar.runner_type = 'browser'
)
ORDER BY run_id DESC, intent_id, brand;

-- ============================================================================
-- 3. Rank Position Changes (Same Brand, Different Ranks in API vs Browser)
-- ============================================================================

SELECT
    m_api.run_id,
    m_api.intent_id,
    m_api.model_provider,
    m_api.normalized_name as brand,
    m_api.rank_position as api_rank,
    m_browser.rank_position as browser_rank,
    (m_browser.rank_position - m_api.rank_position) as rank_change,
    CASE
        WHEN m_browser.rank_position < m_api.rank_position THEN 'IMPROVED_IN_BROWSER'
        WHEN m_browser.rank_position > m_api.rank_position THEN 'DECLINED_IN_BROWSER'
        ELSE 'SAME_RANK'
    END as rank_direction
FROM mentions m_api
INNER JOIN answers_raw ar_api ON
    m_api.run_id = ar_api.run_id
    AND m_api.intent_id = ar_api.intent_id
    AND m_api.model_provider = ar_api.model_provider
    AND m_api.model_name = ar_api.model_name
    AND ar_api.runner_type = 'api'
INNER JOIN mentions m_browser ON
    m_api.run_id = m_browser.run_id
    AND m_api.intent_id = m_browser.intent_id
    AND m_api.normalized_name = m_browser.normalized_name
INNER JOIN answers_raw ar_browser ON
    m_browser.run_id = ar_browser.run_id
    AND m_browser.intent_id = ar_browser.intent_id
    AND m_browser.model_provider = ar_browser.model_provider
    AND m_browser.model_name = ar_browser.model_name
    AND ar_browser.runner_type = 'browser'
WHERE m_api.rank_position != m_browser.rank_position  -- Only show changes
ORDER BY m_api.run_id DESC, m_api.intent_id, ABS(m_browser.rank_position - m_api.rank_position) DESC;

-- ============================================================================
-- 4. Divergence Rate Summary (by Provider)
-- ============================================================================

WITH paired_responses AS (
    SELECT
        ar_api.run_id,
        ar_api.intent_id,
        ar_api.model_provider,
        ar_api.answer_text as api_text,
        ar_browser.answer_text as browser_text,
        -- Simple divergence check (text differs)
        CASE WHEN ar_api.answer_text != ar_browser.answer_text THEN 1 ELSE 0 END as diverged
    FROM answers_raw ar_api
    INNER JOIN answers_raw ar_browser ON
        ar_api.run_id = ar_browser.run_id
        AND ar_api.intent_id = ar_browser.intent_id
        AND ar_api.model_provider = ar_browser.model_provider  -- Same provider
    WHERE ar_api.runner_type = 'api' AND ar_browser.runner_type = 'browser'
)
SELECT
    model_provider,
    COUNT(*) as total_paired_queries,
    SUM(diverged) as divergent_queries,
    ROUND(CAST(SUM(diverged) AS FLOAT) / COUNT(*) * 100, 2) as divergence_rate_pct,
    COUNT(*) - SUM(diverged) as identical_queries
FROM paired_responses
GROUP BY model_provider
ORDER BY divergence_rate_pct DESC;

-- ============================================================================
-- 5. Temporal Trends (Divergence Over Time)
-- ============================================================================

WITH daily_divergence AS (
    SELECT
        DATE(r.timestamp_utc) as run_date,
        ar_api.model_provider,
        COUNT(DISTINCT ar_api.intent_id) as total_queries,
        SUM(
            CASE WHEN ar_api.answer_text != ar_browser.answer_text THEN 1 ELSE 0 END
        ) as divergent_queries
    FROM runs r
    INNER JOIN answers_raw ar_api ON
        r.run_id = ar_api.run_id AND ar_api.runner_type = 'api'
    INNER JOIN answers_raw ar_browser ON
        ar_api.run_id = ar_browser.run_id
        AND ar_api.intent_id = ar_browser.intent_id
        AND ar_api.model_provider = ar_browser.model_provider
        AND ar_browser.runner_type = 'browser'
    GROUP BY run_date, ar_api.model_provider
)
SELECT
    run_date,
    model_provider,
    total_queries,
    divergent_queries,
    ROUND(CAST(divergent_queries AS FLOAT) / total_queries * 100, 2) as divergence_rate_pct,
    -- 7-day moving average (if enough data)
    ROUND(
        AVG(CAST(divergent_queries AS FLOAT) / total_queries * 100)
        OVER (
            PARTITION BY model_provider
            ORDER BY run_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ),
        2
    ) as ma_7day_pct
FROM daily_divergence
ORDER BY run_date DESC, model_provider;

-- ============================================================================
-- 6. Screenshot Inventory (For Creating Comparison Reports)
-- ============================================================================

SELECT
    r.run_id,
    ar.intent_id,
    ar.model_provider,
    ar.runner_name,
    ar.screenshot_path,
    ar.html_snapshot_path,
    ar.session_id,
    LENGTH(ar.answer_text) as answer_length
FROM runs r
INNER JOIN answers_raw ar ON r.run_id = ar.run_id
WHERE ar.runner_type = 'browser'
    AND ar.screenshot_path IS NOT NULL
ORDER BY r.timestamp_utc DESC;

-- ============================================================================
-- 7. Cost Comparison (API vs Browser)
-- ============================================================================

WITH cost_by_runner AS (
    SELECT
        r.run_id,
        ar.runner_type,
        COUNT(*) as num_queries,
        SUM(ar.estimated_cost_usd) as total_cost_usd,
        AVG(ar.estimated_cost_usd) as avg_cost_per_query
    FROM runs r
    INNER JOIN answers_raw ar ON r.run_id = ar.run_id
    GROUP BY r.run_id, ar.runner_type
)
SELECT
    run_id,
    MAX(CASE WHEN runner_type = 'api' THEN num_queries END) as api_queries,
    MAX(CASE WHEN runner_type = 'api' THEN total_cost_usd END) as api_cost,
    MAX(CASE WHEN runner_type = 'browser' THEN num_queries END) as browser_queries,
    MAX(CASE WHEN runner_type = 'browser' THEN total_cost_usd END) as browser_cost,
    -- Browser cost is $0 (free tier) but has Steel session costs not tracked yet
    MAX(CASE WHEN runner_type = 'api' THEN total_cost_usd END) as total_llm_cost
FROM cost_by_runner
GROUP BY run_id
ORDER BY run_id DESC;

-- ============================================================================
-- 8. Export Data for Analysis (CSV-friendly format)
-- ============================================================================

-- Use this query to export data for analysis in Python/R/Excel
.mode csv
.headers on
.output api_vs_browser_export.csv

SELECT
    r.run_id,
    r.timestamp_utc,
    ar_api.intent_id,
    ar_api.model_provider,
    ar_api.model_name as api_model,
    ar_api.answer_text as api_answer,
    LENGTH(ar_api.answer_text) as api_length,
    ar_api.estimated_cost_usd as api_cost,
    ar_browser.runner_name as browser_runner,
    ar_browser.answer_text as browser_answer,
    LENGTH(ar_browser.answer_text) as browser_length,
    ar_browser.screenshot_path,
    -- Brand counts
    (SELECT COUNT(*) FROM mentions m WHERE m.run_id = ar_api.run_id AND m.intent_id = ar_api.intent_id AND EXISTS (
        SELECT 1 FROM answers_raw a WHERE a.run_id = m.run_id AND a.intent_id = m.intent_id AND a.runner_type = 'api'
    )) as api_brand_count,
    (SELECT COUNT(*) FROM mentions m WHERE m.run_id = ar_browser.run_id AND m.intent_id = ar_browser.intent_id AND EXISTS (
        SELECT 1 FROM answers_raw a WHERE a.run_id = m.run_id AND a.intent_id = m.intent_id AND a.runner_type = 'browser'
    )) as browser_brand_count
FROM runs r
INNER JOIN answers_raw ar_api ON
    r.run_id = ar_api.run_id AND ar_api.runner_type = 'api'
INNER JOIN answers_raw ar_browser ON
    ar_api.run_id = ar_browser.run_id
    AND ar_api.intent_id = ar_browser.intent_id
    AND ar_api.model_provider = ar_browser.model_provider
    AND ar_browser.runner_type = 'browser'
ORDER BY r.timestamp_utc DESC;

.output stdout

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

/*

1. Find all paired responses from latest run:

    SELECT * FROM (
        -- Query #1 from above
    )
    WHERE run_id = (SELECT run_id FROM runs ORDER BY timestamp_utc DESC LIMIT 1);

2. Count unique brands per channel:

    SELECT
        runner_type,
        COUNT(DISTINCT normalized_name) as unique_brands
    FROM mentions m
    INNER JOIN answers_raw ar USING (run_id, intent_id, model_provider, model_name)
    WHERE run_id = 'YOUR_RUN_ID'
    GROUP BY runner_type;

3. Export for Python analysis:

    sqlite3 llm_answers.db "SELECT ... FROM ..." | python analyze_divergence.py

*/
