# GA4/GSC Trends Integration - Research & Implementation Plan

**Status**: Research Complete
**Date**: 2025-11-09
**Author**: Claude (Session: claude/research-mention-trends-ga4-011CUxNJR7uoad9ytAkvhjDL)

## Executive Summary

This document outlines a comprehensive plan for implementing a **mention trends feature** that correlates LLM brand mention data with real-world traffic and search performance metrics from Google Analytics 4 (GA4) and Google Search Console (GSC).

**Core Value Proposition**: Enable users to answer the critical question: *"Does increased LLM visibility correlate with actual website traffic and search rankings?"*

## 1. Current State Analysis

### 1.1 Existing LLM Answer Watcher Capabilities

**Database Schema (v5):**
- `runs` - CLI execution metadata
- `answers_raw` - Full LLM responses with tokens, cost, web search results
- `mentions` - Exploded brand mentions with rank, sentiment, context
- `operations` - Post-intent operation results
- `intent_classifications` - Query intent metadata (transactional/informational/navigational)
- `intent_classification_cache` - Cache for intent classification results

**Key Metrics Tracked:**
- Brand mention frequency over time
- Rank position in LLM responses
- Sentiment (positive/neutral/negative)
- Mention context (primary_recommendation, alternative_listing, etc.)
- Query intent classification
- Token usage and cost per query

**Time Series Capability:**
- All data timestamped with UTC (`timestamp_utc` in ISO 8601 format)
- Indexed by timestamp for efficient time-based queries
- Daily/weekly/monthly aggregation possible via SQL

### 1.2 Data Gap Analysis

**What We Have:**
- ✅ Historical LLM mention data with timestamps
- ✅ Brand-level aggregation (normalized_name)
- ✅ Intent-level tracking (which queries mention which brands)
- ✅ Rank position tracking
- ✅ Sentiment and context classification

**What We Need:**
- ❌ GA4 traffic data (sessions, users, pageviews, conversions)
- ❌ GSC search performance (impressions, clicks, CTR, position)
- ❌ Correlation analysis (statistical relationship between mentions and traffic)
- ❌ Time-series alignment (matching LLM data with GA4/GSC data on common dates)
- ❌ Attribution logic (did LLM mention lead to traffic?)

## 2. External API Research

### 2.1 Google Analytics 4 (GA4) API

**Official API:** Google Analytics Data API (v1beta)
**Python Package:** `google-analytics-data`
**Documentation:** https://developers.google.com/analytics/devguides/reporting/data/v1

#### Authentication Methods

1. **Service Account (Recommended for Automation)**
   - JSON key file downloaded from Google Cloud Console
   - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
   - Service account email must be added to GA4 property with "Viewer" role
   - No user interaction required (perfect for CLI automation)

2. **OAuth2 (User Authentication)**
   - Requires browser flow for initial authentication
   - Stores token in `token.json` for reuse
   - Better for user-facing apps, not ideal for CLI automation

#### Key Metrics Available

**Traffic Metrics:**
- `activeUsers` - Number of distinct users
- `sessions` - Number of sessions
- `screenPageViews` - Total pageviews
- `averageSessionDuration` - Average session length
- `bounceRate` - Percentage of single-page sessions
- `conversions` - Total conversion events
- `eventCount` - Total events

**Dimensions:**
- `date` - Date in YYYYMMDD format
- `landingPage` - Entry page URL
- `sessionSource` - Traffic source (organic, direct, referral)
- `sessionMedium` - Traffic medium (organic, cpc, referral)
- `country` - User country
- `deviceCategory` - Device type (desktop, mobile, tablet)

#### Sample Query Pattern

```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric

client = BetaAnalyticsDataClient()

request = RunReportRequest(
    property=f"properties/{property_id}",
    date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
    dimensions=[Dimension(name="date"), Dimension(name="landingPage")],
    metrics=[Metric(name="activeUsers"), Metric(name="sessions")]
)

response = client.run_report(request)
```

#### Rate Limits
- **Quota:** 25,000 tokens per day per project (free tier)
- **Concurrent requests:** 10 requests per second
- **Best practice:** Batch requests, cache results daily

### 2.2 Google Search Console (GSC) API

**Official API:** Search Console API (v1)
**Python Package:** `google-api-python-client`
**Documentation:** https://developers.google.com/webmaster-tools/v1/api_reference_index

#### Authentication Methods

1. **Service Account (Recommended)**
   - JSON key file from Google Cloud Console
   - Service account email must be added to GSC property as "Owner" or "Full" user
   - No browser interaction needed

2. **OAuth2 (User Authentication)**
   - Browser flow for initial auth
   - Stores credentials in file
   - Requires `https://www.googleapis.com/auth/webmasters.readonly` scope

#### Key Metrics Available

**Search Performance Metrics:**
- `clicks` - Total clicks from search results
- `impressions` - Total impressions in search results
- `ctr` - Click-through rate (clicks / impressions)
- `position` - Average ranking position in search results

**Dimensions:**
- `date` - Date of search data
- `query` - Search query (keyword)
- `page` - Landing page URL
- `country` - User country
- `device` - Device type (DESKTOP, MOBILE, TABLET)
- `searchAppearance` - How result appeared (AMP, video, etc.)

#### Sample Query Pattern

```python
from googleapiclient.discovery import build
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'service_account.json',
    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
)

service = build('searchconsole', 'v1', credentials=credentials)

request = {
    'startDate': '2025-10-01',
    'endDate': '2025-11-01',
    'dimensions': ['date', 'query', 'page'],
    'rowLimit': 25000
}

response = service.searchanalytics().query(
    siteUrl='https://yourdomain.com',
    body=request
).execute()
```

#### Rate Limits
- **Quota:** 1,200 queries per minute per project
- **Row limit:** 25,000 rows per request
- **Date range:** 16 months of historical data available
- **Best practice:** Use `startRow` pagination for large datasets

### 2.3 Comparison: GA4 vs GSC

| Aspect | GA4 | GSC |
|--------|-----|-----|
| **Focus** | On-site behavior after arrival | Pre-click search performance |
| **Metrics** | Sessions, users, conversions | Clicks, impressions, rankings |
| **Attribution** | Can track referrer sources | Only Google Search data |
| **Granularity** | Event-level tracking | Query-level aggregation |
| **Use Case** | Traffic trends, conversion impact | Search visibility, keyword rankings |

**Key Insight:** Both APIs complement each other:
- **GSC** tells us: "Brand X ranks #3 for 'best CRM tools' with 1,000 impressions"
- **GA4** tells us: "We got 50 sessions from organic search that converted"
- **LLM Answer Watcher** tells us: "GPT-4 mentions Brand X at rank #2"

## 3. Proposed Architecture

### 3.1 High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                   LLM Answer Watcher Core                   │
│  (Existing: LLM queries, mention extraction, SQLite storage)│
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ New Integration Layer
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              External Analytics Module                       │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ GA4 Client  │  │ GSC Client  │  │ Correlation Eng. │   │
│  └─────────────┘  └─────────────┘  └──────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Data Storage
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Extended SQLite Schema                      │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ ga4_metrics    │  │ gsc_metrics    │  │ correlations │ │
│  │ (v6 migration) │  │ (v6 migration) │  │ (v6 schema)  │ │
│  └────────────────┘  └────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                     │
                     │ User Interface
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      CLI Commands                            │
│  • llm-answer-watcher trends sync                           │
│  • llm-answer-watcher trends correlate                      │
│  • llm-answer-watcher trends report                         │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Module Structure

**New Modules:**

```
llm_answer_watcher/
├── analytics/                    # NEW MODULE
│   ├── __init__.py
│   ├── ga4_client.py            # GA4 API client
│   ├── gsc_client.py            # GSC API client
│   ├── models.py                # Pydantic models for GA4/GSC data
│   ├── sync.py                  # Data sync orchestration
│   └── correlation.py           # Statistical correlation analysis
├── storage/
│   ├── db.py                    # Existing (extend for v6 schema)
│   └── migrations.py            # Add _migrate_to_v6()
└── cli.py                       # Add 'trends' command group
```

### 3.3 Database Schema Extension (v6 Migration)

#### Table: `ga4_metrics`

Stores daily GA4 traffic metrics.

```sql
CREATE TABLE ga4_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id TEXT NOT NULL,           -- GA4 property ID
    date TEXT NOT NULL,                  -- YYYY-MM-DD format
    landing_page TEXT,                   -- URL (optional, for page-level)
    source TEXT,                         -- Traffic source (organic, direct, etc.)
    medium TEXT,                         -- Traffic medium (organic, cpc, etc.)
    active_users INTEGER DEFAULT 0,      -- Daily active users
    sessions INTEGER DEFAULT 0,          -- Total sessions
    page_views INTEGER DEFAULT 0,        -- Total pageviews
    avg_session_duration REAL DEFAULT 0, -- Average session duration (seconds)
    bounce_rate REAL DEFAULT 0,          -- Bounce rate (0-1)
    conversions INTEGER DEFAULT 0,       -- Total conversions
    synced_at_utc TEXT NOT NULL,         -- When data was fetched from GA4
    UNIQUE(property_id, date, landing_page, source, medium)
);

CREATE INDEX idx_ga4_date ON ga4_metrics(date);
CREATE INDEX idx_ga4_property ON ga4_metrics(property_id);
CREATE INDEX idx_ga4_source ON ga4_metrics(source);
```

#### Table: `gsc_metrics`

Stores daily GSC search performance metrics.

```sql
CREATE TABLE gsc_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_url TEXT NOT NULL,              -- GSC property URL
    date TEXT NOT NULL,                  -- YYYY-MM-DD format
    query TEXT,                          -- Search keyword (optional)
    page TEXT,                           -- Landing page URL (optional)
    country TEXT,                        -- Country code (optional)
    device TEXT,                         -- DESKTOP, MOBILE, TABLET (optional)
    clicks INTEGER DEFAULT 0,            -- Total clicks
    impressions INTEGER DEFAULT 0,       -- Total impressions
    ctr REAL DEFAULT 0,                  -- Click-through rate (0-1)
    position REAL DEFAULT 0,             -- Average search ranking position
    synced_at_utc TEXT NOT NULL,         -- When data was fetched from GSC
    UNIQUE(site_url, date, query, page, country, device)
);

CREATE INDEX idx_gsc_date ON gsc_metrics(date);
CREATE INDEX idx_gsc_site ON gsc_metrics(site_url);
CREATE INDEX idx_gsc_query ON gsc_metrics(query);
CREATE INDEX idx_gsc_page ON gsc_metrics(page);
```

#### Table: `trend_correlations`

Stores computed correlation analyses between LLM mentions and GA4/GSC metrics.

```sql
CREATE TABLE trend_correlations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL,           -- Unique ID for this analysis run
    brand_name TEXT NOT NULL,            -- Brand being analyzed
    normalized_name TEXT NOT NULL,       -- Normalized brand name
    start_date TEXT NOT NULL,            -- YYYY-MM-DD
    end_date TEXT NOT NULL,              -- YYYY-MM-DD
    metric_type TEXT NOT NULL,           -- 'ga4_sessions', 'gsc_clicks', etc.
    correlation_coefficient REAL,        -- Pearson correlation (-1 to 1)
    p_value REAL,                        -- Statistical significance
    lag_days INTEGER,                    -- Time lag for max correlation (e.g., +7 days)
    sample_size INTEGER,                 -- Number of data points
    mention_trend TEXT,                  -- 'increasing', 'decreasing', 'stable'
    traffic_trend TEXT,                  -- 'increasing', 'decreasing', 'stable'
    computed_at_utc TEXT NOT NULL,       -- When analysis was performed
    notes TEXT,                          -- Additional context or insights
    UNIQUE(analysis_id, brand_name, metric_type, lag_days)
);

CREATE INDEX idx_corr_brand ON trend_correlations(normalized_name);
CREATE INDEX idx_corr_metric ON trend_correlations(metric_type);
CREATE INDEX idx_corr_date_range ON trend_correlations(start_date, end_date);
```

### 3.4 Configuration Extension

Extend `watcher.config.yaml` to support GA4/GSC credentials:

```yaml
# Existing fields (brand, aliases, intents, models, etc.)
...

# New analytics section
analytics:
  ga4:
    enabled: true
    property_id: "123456789"  # GA4 property ID
    credentials_path: "${GA4_SERVICE_ACCOUNT_PATH}"  # Path to service account JSON
    sync_frequency: "daily"   # daily, weekly, manual
    lookback_days: 90         # How far back to sync data
    metrics:
      - active_users
      - sessions
      - page_views
      - conversions
    dimensions:
      - date
      - landing_page
      - source
      - medium

  gsc:
    enabled: true
    site_url: "https://yourdomain.com"
    credentials_path: "${GSC_SERVICE_ACCOUNT_PATH}"  # Path to service account JSON
    sync_frequency: "daily"
    lookback_days: 90
    metrics:
      - clicks
      - impressions
      - ctr
      - position
    dimensions:
      - date
      - query
      - page
      - device

  correlation:
    enabled: true
    min_data_points: 14       # Minimum days of data needed
    lag_days_range: [-7, 14]  # Test lags from -7 to +14 days
    significance_level: 0.05  # p-value threshold for statistical significance
```

### 3.5 Pydantic Models

```python
# llm_answer_watcher/analytics/models.py

from pydantic import BaseModel, Field
from datetime import date

class GA4Metric(BaseModel):
    """GA4 daily traffic metric."""
    property_id: str
    date: date
    landing_page: str | None = None
    source: str | None = None
    medium: str | None = None
    active_users: int = 0
    sessions: int = 0
    page_views: int = 0
    avg_session_duration: float = 0.0
    bounce_rate: float = 0.0
    conversions: int = 0

class GSCMetric(BaseModel):
    """GSC daily search performance metric."""
    site_url: str
    date: date
    query: str | None = None
    page: str | None = None
    country: str | None = None
    device: str | None = None
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float = 0.0

class CorrelationResult(BaseModel):
    """Statistical correlation between LLM mentions and traffic/search metrics."""
    analysis_id: str
    brand_name: str
    normalized_name: str
    start_date: date
    end_date: date
    metric_type: str  # 'ga4_sessions', 'gsc_clicks', etc.
    correlation_coefficient: float = Field(ge=-1.0, le=1.0)
    p_value: float = Field(ge=0.0, le=1.0)
    lag_days: int = 0  # Optimal time lag
    sample_size: int
    mention_trend: str  # 'increasing', 'decreasing', 'stable'
    traffic_trend: str  # 'increasing', 'decreasing', 'stable'
    notes: str | None = None
```

## 4. Implementation Plan

### 4.1 Phased Approach

#### Phase 1: Data Sync (Foundation) - Estimated 2-3 days

**Goal:** Fetch and store GA4/GSC data in local SQLite database.

**Tasks:**
1. ✅ Create `analytics/` module structure
2. ✅ Implement `analytics/models.py` with Pydantic schemas
3. ✅ Implement `analytics/ga4_client.py`:
   - Service account authentication
   - Date range queries
   - Metric/dimension selection
   - Error handling and retry logic (use `tenacity`)
   - Rate limit handling
4. ✅ Implement `analytics/gsc_client.py`:
   - Service account authentication
   - Query pagination (25K row limit)
   - Date range queries
   - Error handling and retry logic
5. ✅ Extend `storage/migrations.py` with `_migrate_to_v6()`
6. ✅ Implement `analytics/sync.py`:
   - Orchestrate GA4 + GSC syncs
   - Handle date range calculations (lookback)
   - Deduplication (UNIQUE constraints)
   - Logging and progress tracking
7. ✅ Add CLI command: `llm-answer-watcher trends sync`
   - Flags: `--ga4`, `--gsc`, `--all`, `--start-date`, `--end-date`
   - Output: Summary of records synced

**Testing:**
- Mock GA4/GSC API responses with `pytest-httpx`
- Test date range logic
- Test deduplication
- Test error handling (API failures, rate limits)

#### Phase 2: Time-Series Alignment (Data Prep) - Estimated 1-2 days

**Goal:** Create SQL views that align LLM mentions with GA4/GSC data on common dates.

**Tasks:**
1. ✅ Create SQL views:
   - `v_daily_mentions_summary`: Daily mention counts per brand
   - `v_daily_ga4_summary`: Daily GA4 metrics aggregated
   - `v_daily_gsc_summary`: Daily GSC metrics aggregated
   - `v_aligned_trends`: JOIN all three on date
2. ✅ Add helper functions in `analytics/sync.py`:
   - `get_mention_time_series(brand, start_date, end_date)` → list of daily counts
   - `get_ga4_time_series(metric, start_date, end_date)` → list of daily values
   - `get_gsc_time_series(metric, start_date, end_date)` → list of daily values

**Testing:**
- Test SQL views with sample data
- Verify date alignment (handle missing dates with NULL or 0)

#### Phase 3: Correlation Analysis (Insights) - Estimated 2-3 days

**Goal:** Compute statistical correlations between LLM mentions and GA4/GSC metrics.

**Tasks:**
1. ✅ Add dependencies:
   - `scipy` (for Pearson correlation, statistical tests)
   - `pandas` (optional, for easier time-series manipulation)
2. ✅ Implement `analytics/correlation.py`:
   - `compute_pearson_correlation(x, y)` → (r, p_value)
   - `find_optimal_lag(mention_series, metric_series, lag_range)` → lag_days
   - `classify_trend(time_series)` → 'increasing', 'decreasing', 'stable'
   - `run_correlation_analysis(brand, metric_type, start_date, end_date)` → CorrelationResult
3. ✅ Store results in `trend_correlations` table
4. ✅ Add CLI command: `llm-answer-watcher trends correlate`
   - Flags: `--brand`, `--metric`, `--start-date`, `--end-date`, `--lag-range`
   - Output: Correlation coefficient, p-value, interpretation

**Testing:**
- Unit tests with synthetic time series
- Test edge cases (all zeros, perfect correlation, no correlation)
- Test lag detection (e.g., traffic increases 7 days after mention spike)

#### Phase 4: Visualization & Reports (User-Facing) - Estimated 2-3 days

**Goal:** Generate HTML reports with charts showing mention trends vs traffic/search trends.

**Tasks:**
1. ✅ Add dependencies:
   - `plotly` or `matplotlib` for charts
   - Extend existing Jinja2 templates
2. ✅ Extend `report/generator.py`:
   - Add `generate_trends_report(brand, start_date, end_date)` → HTML
   - Include charts:
     - Line chart: Daily mentions vs GA4 sessions (dual Y-axis)
     - Line chart: Daily mentions vs GSC clicks (dual Y-axis)
     - Scatter plot: Mentions vs Sessions (with trend line)
     - Table: Top correlations summary
3. ✅ Add CLI command: `llm-answer-watcher trends report`
   - Flags: `--brand`, `--start-date`, `--end-date`, `--output`
   - Output: Standalone HTML report

**Testing:**
- Visual regression tests
- Test with real sample data
- Cross-browser rendering (Chrome, Firefox, Safari)

### 4.2 Milestones

| Milestone | Deliverable | ETA |
|-----------|-------------|-----|
| M1: Data Sync | GA4/GSC data in SQLite | Day 3 |
| M2: Alignment | SQL views + time-series helpers | Day 5 |
| M3: Correlation | Statistical analysis working | Day 8 |
| M4: Reports | HTML trends reports | Day 11 |

**Total Estimated Timeline:** 10-12 development days

### 4.3 Success Criteria

**Must Have:**
- ✅ GA4 data syncs successfully to SQLite
- ✅ GSC data syncs successfully to SQLite
- ✅ Correlation coefficient computed for mention vs traffic
- ✅ Statistical significance (p-value) reported
- ✅ CLI commands work in human/agent/quiet modes
- ✅ 80%+ test coverage for new modules

**Nice to Have:**
- ✅ Auto-sync on schedule (cron-like)
- ✅ Lag analysis (detect delayed effects)
- ✅ Interactive charts in HTML reports
- ✅ Multi-brand comparison in single report
- ✅ Export to CSV for further analysis

## 5. Statistical Methodology

### 5.1 Correlation Analysis

**Primary Metric:** Pearson correlation coefficient (r)

```python
from scipy.stats import pearsonr

r, p_value = pearsonr(mention_counts, traffic_values)

# Interpretation:
# r = 1.0  → Perfect positive correlation
# r = 0.0  → No correlation
# r = -1.0 → Perfect negative correlation
# p_value < 0.05 → Statistically significant
```

**Limitations:**
- Correlation ≠ causation
- Assumes linear relationship
- Sensitive to outliers
- Requires sufficient sample size (n ≥ 14 recommended)

**Alternatives to Consider:**
- **Spearman rank correlation** (non-linear relationships)
- **Cross-correlation with lag** (time-shifted relationships)
- **Granger causality test** (directional causality)

### 5.2 Lag Analysis

LLM mentions may precede traffic changes by several days (attribution lag).

```python
def find_optimal_lag(mentions, traffic, lag_range=range(-7, 15)):
    """
    Find the time lag that maximizes correlation.

    Positive lag = traffic lags behind mentions (e.g., lag=7 means traffic
                   increases 7 days AFTER mention spike)
    Negative lag = mentions lag behind traffic
    """
    correlations = {}

    for lag in lag_range:
        if lag > 0:
            # Shift traffic forward (mentions lead)
            r, p = pearsonr(mentions[:-lag], traffic[lag:])
        elif lag < 0:
            # Shift mentions forward (traffic leads)
            r, p = pearsonr(mentions[-lag:], traffic[:lag])
        else:
            # No shift
            r, p = pearsonr(mentions, traffic)

        correlations[lag] = (r, p)

    # Find lag with max absolute correlation
    optimal_lag = max(correlations, key=lambda k: abs(correlations[k][0]))
    return optimal_lag, correlations[optimal_lag]
```

### 5.3 Trend Classification

Simple heuristic to classify time series trends:

```python
def classify_trend(values):
    """
    Classify trend as 'increasing', 'decreasing', or 'stable'.

    Uses linear regression slope and R² to determine trend strength.
    """
    from scipy.stats import linregress

    x = list(range(len(values)))
    slope, _, r_value, p_value, _ = linregress(x, values)

    r_squared = r_value ** 2

    if r_squared < 0.3:
        return 'stable'  # Weak trend
    elif slope > 0:
        return 'increasing'
    else:
        return 'decreasing'
```

## 6. Use Cases & Examples

### 6.1 Use Case 1: Validate LLM Visibility Impact

**Scenario:** Marketing team invests in AI SEO (optimizing for LLM mentions).

**Question:** "Did our AI SEO efforts lead to increased organic traffic?"

**Workflow:**
1. Run LLM queries weekly: `llm-answer-watcher run --config watcher.yaml`
2. Sync GA4 data weekly: `llm-answer-watcher trends sync --ga4`
3. Analyze correlation monthly: `llm-answer-watcher trends correlate --brand OurBrand --metric ga4_sessions --start-date 2025-08-01 --end-date 2025-11-01`
4. Generate report: `llm-answer-watcher trends report --brand OurBrand --output trends_report.html`

**Expected Output:**
```
Correlation Analysis: OurBrand (2025-08-01 to 2025-11-01)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Metric: ga4_sessions
Correlation Coefficient: 0.72 (Strong positive)
P-value: 0.003 (Statistically significant)
Optimal Lag: +5 days (Traffic increases 5 days after mention spike)
Mention Trend: increasing
Traffic Trend: increasing

Interpretation:
✅ Strong evidence that LLM mentions correlate with traffic growth.
✅ 5-day lag suggests attribution window for LLM-driven traffic.
```

### 6.2 Use Case 2: Competitive Intelligence

**Scenario:** Monitor competitor mentions vs our own.

**Question:** "How do competitor LLM mentions correlate with their search rankings?"

**Workflow:**
1. Track multiple brands in config: `brands.my_brand` + `brands.competitors`
2. Sync GSC data: `llm-answer-watcher trends sync --gsc`
3. Compare correlations:
   ```
   llm-answer-watcher trends correlate --brand Competitor1 --metric gsc_clicks
   llm-answer-watcher trends correlate --brand OurBrand --metric gsc_clicks
   ```

**Expected Output:**
```
Brand            Correlation  P-value  Mention Trend  Click Trend
──────────────── ──────────── ──────── ─────────────── ────────────
Competitor1      0.65         0.012    increasing      increasing
OurBrand         0.45         0.089    stable          stable
```

### 6.3 Use Case 3: Attribution Windows

**Scenario:** Understand time lag between LLM mentions and conversions.

**Question:** "How long does it take for an LLM mention to drive a conversion?"

**Workflow:**
1. Sync GA4 conversion data: `llm-answer-watcher trends sync --ga4`
2. Run lag analysis: `llm-answer-watcher trends correlate --brand OurBrand --metric ga4_conversions --lag-range -7,30`

**Expected Output:**
```
Optimal Lag: +14 days
Correlation at lag +14: 0.58 (p=0.021)

Insight: Conversions peak 2 weeks after LLM mention spikes.
This suggests a research → consideration → decision funnel.
```

## 7. Technical Considerations

### 7.1 API Costs & Quotas

**GA4 API:**
- Free tier: 25,000 tokens/day (sufficient for daily syncs)
- Tokens consumed per request: ~10 tokens
- Daily sync cost: ~100 tokens (negligible)

**GSC API:**
- Free tier: 1,200 queries/minute (very generous)
- Row limit: 25,000 rows/request
- Typical daily sync: 1-10 requests (well within quota)

**Recommendation:** Start with daily syncs; upgrade to hourly if needed.

### 7.2 Data Freshness

**GA4 Data Lag:**
- Real-time data: Available with ~30 minutes lag
- Standard data: Fully processed within 24-48 hours
- **Recommendation:** Sync data with 2-day lag to ensure completeness

**GSC Data Lag:**
- Data typically lags 2-3 days
- **Recommendation:** Sync data with 3-day lag

### 7.3 Privacy & Compliance

**GDPR/CCPA Considerations:**
- GA4 and GSC aggregate data (no PII)
- Service account access is read-only
- Store credentials in environment variables (never commit to git)
- Document data retention policy in `PRIVACY.md`

**Security Best Practices:**
- Use service accounts (no user passwords)
- Rotate service account keys annually
- Apply principle of least privilege (read-only scopes)
- Encrypt credentials at rest (use OS keychain or secrets manager)

### 7.4 Scalability

**SQLite Performance:**
- Handles millions of rows efficiently with proper indexing
- Daily metrics: ~365 rows/year/brand (very small)
- GSC query-level data: ~10K-100K rows/year (manageable)

**If SQLite becomes a bottleneck:**
- Consider PostgreSQL backend (add `psycopg2` support)
- Use partitioning (separate tables per year)
- Implement archival strategy (compress old data)

### 7.5 Error Handling

**Retry Strategy:**
- Use `tenacity` library (already in dependencies)
- Exponential backoff: 2s, 4s, 8s, 16s
- Max retries: 4 attempts
- Retry on: 429 (rate limit), 500 (server error), 503 (unavailable)

**Graceful Degradation:**
- If GA4 sync fails, GSC sync should still proceed
- Partial data is better than no data
- Log errors but don't crash CLI

## 8. Alternative Approaches Considered

### 8.1 Real-Time Attribution (Rejected)

**Idea:** Track individual user journeys from LLM mention → GA4 session.

**Why Rejected:**
- Requires tracking pixels or UTM parameters in LLM responses (not feasible)
- LLMs don't provide referrer data
- Privacy concerns with user-level tracking

**Conclusion:** Aggregate correlation is more practical and privacy-friendly.

### 8.2 Third-Party Analytics Platforms (Rejected)

**Idea:** Use Mixpanel, Amplitude, or Segment instead of GA4/GSC.

**Why Rejected:**
- Adds external dependency and cost
- GA4/GSC are industry standards (most users already have them)
- BYOK principle: users bring their own analytics

**Conclusion:** Stick with GA4/GSC for maximum compatibility.

### 8.3 Manual CSV Upload (Considered for v2)

**Idea:** Let users upload GA4/GSC data as CSV instead of API integration.

**Pros:**
- No API authentication needed
- Works with any analytics platform
- User controls data freshness

**Cons:**
- Manual process (defeats automation goal)
- No standardized format (parsing challenges)
- Error-prone

**Conclusion:** Implement API-first, add CSV import in v2 if requested.

## 9. Testing Strategy

### 9.1 Unit Tests

**Coverage Targets:**
- `analytics/ga4_client.py`: 80%+
- `analytics/gsc_client.py`: 80%+
- `analytics/correlation.py`: 90%+ (critical business logic)
- `analytics/sync.py`: 75%+

**Mock Strategy:**
- Use `pytest-httpx` to mock GA4/GSC API responses
- Use `freezegun` to mock dates for time-series tests
- Use `tmp_path` fixture for SQLite database tests

### 9.2 Integration Tests

**Test Scenarios:**
1. Full sync workflow (GA4 + GSC → SQLite)
2. Correlation analysis with real sample data
3. CLI commands end-to-end
4. Error handling (API failures, malformed responses)

### 9.3 Sample Data

**Create fixtures:**
- `tests/fixtures/ga4_response.json` - Mock GA4 API response
- `tests/fixtures/gsc_response.json` - Mock GSC API response
- `tests/fixtures/sample_time_series.json` - Known correlation (r=0.8)

## 10. Documentation Requirements

### 10.1 User-Facing Docs

**New documentation pages:**
1. `docs/user-guide/trends-analysis.md` - Overview of trends feature
2. `docs/user-guide/ga4-setup.md` - GA4 service account setup guide
3. `docs/user-guide/gsc-setup.md` - GSC service account setup guide
4. `docs/examples/correlation-example.md` - Step-by-step tutorial

### 10.2 Developer Docs

**Update existing docs:**
1. `CLAUDE.md` - Add analytics module to architecture section
2. `SPECS.md` - Add trends feature specification
3. `TODO.md` - Add new milestone for trends feature

## 11. Rollout Plan

### 11.1 Release Strategy

**Version:** v0.3.0 (Trends & Analytics)

**Release Stages:**
1. **Alpha (Week 1-2):** Internal testing with mock data
2. **Beta (Week 3-4):** Private beta with 5-10 users
3. **General Availability (Week 5):** Public release

### 11.2 Communication

**Announcement Channels:**
- GitHub Release Notes
- Project README update
- Example use cases in docs

**Beta Testers:**
- Recruit users who already have GA4/GSC access
- Request feedback on:
  - Setup complexity (service account auth)
  - CLI UX (command names, flags)
  - Report usefulness (actionable insights?)

## 12. Future Enhancements (Post-v0.3.0)

### 12.1 Advanced Analytics

- **Multivariate correlation:** Analyze multiple brands simultaneously
- **Forecasting:** Predict future traffic based on mention trends (Prophet, ARIMA)
- **Anomaly detection:** Alert when correlations break down (e.g., mentions increase but traffic drops)
- **Segment analysis:** Correlate by device type, country, traffic source

### 12.2 Additional Integrations

- **Adobe Analytics** (enterprise alternative to GA4)
- **Plausible Analytics** (privacy-focused alternative)
- **Matomo** (open-source alternative)
- **SEMrush API** (keyword rankings)
- **Ahrefs API** (backlink tracking)

### 12.3 Automation

- **Scheduled syncs:** Cron job integration (daily GA4/GSC sync)
- **Alerting:** Slack/email notifications when correlations cross thresholds
- **Dashboard:** Web UI for visualizing trends (future SaaS product)

## 13. Open Questions & Risks

### 13.1 Open Questions

1. **What minimum sample size is needed for reliable correlation?**
   - Hypothesis: 14 days (2 weeks) minimum
   - Need to validate with statistical power analysis

2. **How do we handle seasonality?**
   - Example: E-commerce traffic spikes in Q4, LLM mentions may not
   - Solution: Detrend data before computing correlation (subtract moving average)

3. **Should we support multiple GA4 properties?**
   - Use case: Company has separate properties for different products
   - Solution: Allow array of `property_id` in config

4. **How do we handle missing dates in time series?**
   - Example: LLM query skipped on weekends, GA4 has data for all 7 days
   - Solution: Forward-fill or interpolate missing values

### 13.2 Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| GA4 API quota exceeded | High | Low | Implement caching, batch requests |
| GSC data lag (3+ days) | Medium | High | Document expected lag, allow manual refresh |
| Correlation misinterpretation | High | Medium | Add clear disclaimers ("correlation ≠ causation") |
| Service account setup too complex | Medium | High | Provide step-by-step setup guide with screenshots |
| SQLite performance degrades | Low | Low | Add PostgreSQL support in v0.4.0 |

## 14. Summary & Next Steps

### 14.1 Key Takeaways

✅ **Feasibility:** GA4/GSC integration is technically feasible with existing Python libraries.

✅ **Value:** Correlation analysis provides actionable insights into LLM mention ROI.

✅ **Timeline:** 10-12 development days for complete implementation.

✅ **Complexity:** Moderate (new module, schema migration, statistical analysis).

### 14.2 Recommended Next Steps

1. **Validate assumptions:**
   - Confirm users have GA4/GSC access (survey existing users)
   - Test service account setup complexity (run through guide ourselves)

2. **Spike POC (2 days):**
   - Build minimal GA4 client that fetches last 7 days of sessions
   - Compute simple correlation with existing mention data
   - Validate statistical methodology

3. **If POC succeeds:**
   - Proceed with Phase 1 implementation (Data Sync)
   - Follow milestones outlined in Section 4.2

4. **If POC reveals blockers:**
   - Document blockers in GitHub issue
   - Consider alternative approaches (CSV import, third-party APIs)

### 14.3 Sign-Off

**Document Status:** ✅ Research Complete - Ready for POC
**Approval Needed From:** Product Owner, Tech Lead
**Next Review Date:** After POC completion

---

## References

### API Documentation
- [Google Analytics Data API (GA4)](https://developers.google.com/analytics/devguides/reporting/data/v1)
- [Google Search Console API](https://developers.google.com/webmaster-tools/v1/api_reference_index)
- [google-analytics-data Python Library](https://pypi.org/project/google-analytics-data/)
- [google-api-python-client](https://pypi.org/project/google-api-python-client/)

### Statistical Methods
- [Pearson Correlation (SciPy)](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html)
- [Cross-Correlation (Wikipedia)](https://en.wikipedia.org/wiki/Cross-correlation)
- [Granger Causality Test (statsmodels)](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.grangercausalitytests.html)

### Time Series Analysis
- [Prophet (Facebook)](https://facebook.github.io/prophet/)
- [ARIMA Models (statsmodels)](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html)

### LLM Answer Watcher
- [SPECS.md](../../SPECS.md)
- [TODO.md](../../TODO.md)
- [CLAUDE.md](../../CLAUDE.md)
