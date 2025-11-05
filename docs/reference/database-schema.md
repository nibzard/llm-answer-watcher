# Database Schema

SQLite database schema reference.

## Tables

### `schema_version`

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY
);
```

### `runs`

```sql
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    timestamp_utc TEXT NOT NULL,
    config_path TEXT,
    total_cost_usd REAL,
    queries_completed INTEGER,
    queries_failed INTEGER
);
```

### `answers_raw`

```sql
CREATE TABLE answers_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    intent_id TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    tokens_used INTEGER,
    estimated_cost_usd REAL,
    timestamp_utc TEXT NOT NULL,
    UNIQUE(run_id, intent_id, model_provider, model_name)
);
```

### `mentions`

```sql
CREATE TABLE mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    intent_id TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    is_mine BOOLEAN NOT NULL,
    rank_position INTEGER,
    context_snippet TEXT,
    timestamp_utc TEXT NOT NULL,
    UNIQUE(run_id, intent_id, model_provider, model_name, normalized_name)
);
```

## Indexes

```sql
CREATE INDEX idx_mentions_timestamp ON mentions(timestamp_utc);
CREATE INDEX idx_mentions_brand ON mentions(normalized_name);
CREATE INDEX idx_mentions_intent ON mentions(intent_id);
```

See [SQLite Database](../data-analytics/sqlite-database.md) for queries.
