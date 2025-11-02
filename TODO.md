# LLM Answer Watcher - Implementation TODO

This file contains **every task** needed to implement the complete system as defined in [SPECS.md](./SPECS.md).

Tasks are organized by **milestones** that map to development sprints. Use your subagent team:
- **Developer** 👨‍💻 for implementation
- **Tester** 🧪 for comprehensive tests
- **Reviewer** 👁️ for quality validation

---

## Progress Overview

- [ ] Milestone 1: Project skeleton & config
- [ ] Milestone 2: Provider client + runner core
- [ ] Milestone 3: Report generation + CLI
- [ ] Milestone 4: Polish, docs, tests

---

## Milestone 1: Project Skeleton & Config

**Goal:** Load config, init DB, confirm DB tables exist, and validation catches all error cases.

### 1.1 Project Structure Setup

- [x] **Create module directory structure**
  ```
  llm_answer_watcher/
      __init__.py
      config/
          __init__.py
          schema.py
          loader.py
          validators.py
      llm_runner/
          __init__.py
          models.py
          openai_client.py
          runner.py
          retry_config.py
      extractor/
          __init__.py
          parser.py
          mention_detector.py
          rank_extractor.py
      storage/
          __init__.py
          db.py
          writer.py
          layout.py
          migrations.py
      report/
          __init__.py
          generator.py
          cost_formatter.py
          templates/
              report.html.j2
      utils/
          __init__.py
          time.py
          logging.py
          cost.py
          console.py
      cli.py
  ```

- [x] **Create pyproject.toml**
  - Package name: `llm-answer-watcher`
  - Python requirement: `>=3.12,<3.14`
  - Dependencies:
    - `pydantic>=2.0`
    - `pyyaml>=6.0`
    - `httpx>=0.27.0`
    - `tenacity>=8.0`
    - `rapidfuzz>=3.0`
    - `jinja2>=3.1`
    - `typer>=0.12.0`
    - `rich>=13.0`
  - Dev dependencies:
    - `pytest>=8.0`
    - `pytest-httpx>=0.30.0`
    - `pytest-cov>=5.0`
    - `pytest-mock>=3.14.0`
    - `freezegun>=1.5.0`
    - `ruff>=0.4.0`
  - Entry point: `llm-answer-watcher = llm_answer_watcher.cli:main`

- [x] **Create VERSION file**
  - Initial version: `0.1.0`
  - [x 2025-11-02] Completed in commit 59b8304

- [x] **Create SCHEMA_VERSION file**
  - Initial schema version: `1`
  - [x 2025-11-02] Completed in commit 59b8304

- [x] **Verify LICENSE exists** (MIT, already created)
  - [x 2025-11-02] Completed - LICENSE file confirmed present in project root

- [x] **Create requirements.txt** (fallback for pip users)
  - Generate from pyproject.toml
  - [x 2025-11-02] Completed in commit b891d1a

### 1.2 Config Module (config/)

#### 1.2.1 config/schema.py

- [x] **Define Pydantic models:**
  - [x 2025-11-02] Completed all 7 Pydantic models (Intent, Brands, ModelConfig, RunSettings, WatcherConfig, RuntimeModel, RuntimeConfig) with validation in commit 9fc6b73
  - [ ] `Intent` model
    - Fields: `id: str`, `prompt: str`
    - Validator: `id` must be alphanumeric with hyphens/underscores
    - Validator: `prompt` must be at least 10 characters

  - [ ] `Brands` model
    - Fields: `mine: list[str]`, `competitors: list[str]`
    - Validator: All brand aliases must be at least 2 characters
    - Validator: No duplicate aliases across mine and competitors

  - [ ] `ModelConfig` model
    - Fields: `provider: str`, `model_name: str`, `env_api_key: str`
    - Validator: `provider` must be in supported list (openai, anthropic)
    - Validator: `env_api_key` must start with valid format

  - [ ] `RunSettings` model
    - Fields:
      - `output_dir: str` (default: "./output")
      - `sqlite_db_path: str` (default: "./output/watcher.db")
      - `models: list[ModelConfig]`
      - `use_llm_rank_extraction: bool` (default: False)
    - Validator: `output_dir` path is valid
    - Validator: At least one model configured

  - [ ] `WatcherConfig` model (top-level)
    - Fields:
      - `run_settings: RunSettings`
      - `brands: Brands`
      - `intents: list[Intent]`
    - Validator: Intent IDs are unique
    - Validator: At least one intent configured

  - [ ] `RuntimeModel` model
    - Fields: `provider: str`, `model_name: str`, `api_key: str`
    - Note: Never serialize this model (contains secrets)

  - [ ] `RuntimeConfig` model
    - Fields:
      - `run_settings: RunSettings`
      - `brands: Brands`
      - `intents: list[Intent]`
      - `models: list[RuntimeModel]`

#### 1.2.2 config/loader.py

- [x] **Implement `load_config(config_path: str) -> RuntimeConfig`**
  - [x] Load YAML file from path
  - [x] Handle FileNotFoundError with clear message
  - [x] Parse YAML into dict
  - [x] Validate with WatcherConfig Pydantic model
  - [x] Catch ValidationError and provide helpful error messages
  - [x] For each ModelConfig, resolve environment variable
  - [x] Check if env var exists with `os.environ.get()`
  - [x] Raise ValueError if API key env var missing
  - [x] Build list of RuntimeModel instances with resolved keys
  - [x] Construct and return RuntimeConfig
  - [x] Add comprehensive docstring with Args, Returns, Raises
  - [x] **Security:** Never log API keys
  - [x 2025-11-02] Completed in commit 0a0e44f with load_config() and resolve_api_keys() implementation

### 1.3 Utils Module - Time (utils/time.py)

- [x] **Implement UTC timestamp utilities:**
  - [x 2025-11-02] Completed in commit 3dea6bc with 4 UTC functions (utc_now, utc_timestamp, run_id_from_timestamp, parse_timestamp)
  - [x] `utc_now() -> datetime`
    - Return current time in UTC with timezone info

  - [x] `utc_timestamp() -> str`
    - Return ISO 8601 timestamp with 'Z' suffix
    - Format: `YYYY-MM-DDTHH:MM:SSZ`

  - [x] `run_id_from_timestamp(dt: datetime | None = None) -> str`
    - Generate run_id slug from timestamp
    - Format: `YYYY-MM-DDTHH-MM-SSZ` (hyphens instead of colons)
    - Default to current time if dt is None

  - [x] `parse_timestamp(ts: str) -> datetime`
    - Parse ISO 8601 timestamp to datetime
    - Raise ValueError if no 'Z' suffix
    - Raise ValueError if invalid format

### 1.4 Utils Module - Logging (utils/logging.py)

- [x] **Setup structured JSON logging:**
  - [x] Configure Python logging module
  - [x] Set default level to INFO
  - [x] Add --verbose flag support for DEBUG
  - [x] Format logs as JSON with fields:
    - `timestamp`: ISO 8601 UTC
    - `level`: INFO, WARNING, ERROR, DEBUG
    - `component`: module name
    - `message`: human-readable description
    - `context`: dict with additional data
    - `run_id`: current run ID if available

  - [x] Output to stderr (stdout reserved for user output)
  - [x] **Implement redaction for secrets:**
    - Never log API keys
    - Only log last 4 chars if needed: `sk-...X7Z9`

  - [x] Create helper functions:
    - [x] `get_logger(component: str) -> Logger`
    - [x] `log_with_context(level, message, context)`
  - [x 2025-11-02 commit 91d209d] Completed with JSONFormatter, SecretRedactingFilter, setup_logging(), get_logger(), and log_with_context() implementation. All security requirements met (stderr output, UTC timestamps, API key redaction)

### 1.5 Storage Module - Database (storage/db.py)

#### 1.5.1 Schema Definition

- [x] **Implement `init_db_if_needed(db_path: str) -> None`**
  - [x 2025-11-02] Completed in commit 2a474ea with database initialization and schema v1
  - [x] Connect to SQLite database
  - [x] Create `schema_version` table if not exists
  - [x] Create `runs` table if not exists
  - [x] Create `answers_raw` table if not exists
  - [x] Create `mentions` table if not exists
  - [x] Create indexes on common query columns
  - [x] Check current schema version
  - [x] Run migrations if needed (call storage.migrations)
  - [x] Close connection properly

- [x] **Schema: `schema_version` table**
  ```sql
  CREATE TABLE IF NOT EXISTS schema_version (
      version INTEGER PRIMARY KEY,
      applied_at TEXT NOT NULL
  );
  ```
  - [x 2025-11-02 commit 2a474ea] Completed with version tracking

- [x] **Schema: `runs` table**
  ```sql
  CREATE TABLE IF NOT EXISTS runs (
      run_id TEXT PRIMARY KEY,
      timestamp_utc TEXT NOT NULL,
      total_intents INTEGER NOT NULL,
      total_models INTEGER NOT NULL,
      total_cost_usd REAL DEFAULT 0.0
  );
  ```
  - [x 2025-11-02 commit 2a474ea] Completed with cost tracking

- [x] **Schema: `answers_raw` table**
  ```sql
  CREATE TABLE IF NOT EXISTS answers_raw (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id TEXT NOT NULL,
      intent_id TEXT NOT NULL,
      model_provider TEXT NOT NULL,
      model_name TEXT NOT NULL,
      timestamp_utc TEXT NOT NULL,
      prompt TEXT NOT NULL,
      answer_text TEXT NOT NULL,
      answer_length INTEGER NOT NULL,
      usage_meta_json TEXT,
      estimated_cost_usd REAL,
      FOREIGN KEY (run_id) REFERENCES runs(run_id),
      UNIQUE(run_id, intent_id, model_provider, model_name)
  );
  ```
  - [x 2025-11-02 commit 2a474ea] Completed with UNIQUE constraint and foreign key

- [x] **Schema: `mentions` table**
  ```sql
  CREATE TABLE IF NOT EXISTS mentions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id TEXT NOT NULL,
      timestamp_utc TEXT NOT NULL,
      intent_id TEXT NOT NULL,
      model_provider TEXT NOT NULL,
      model_name TEXT NOT NULL,
      brand_name TEXT NOT NULL,
      normalized_name TEXT NOT NULL,
      is_mine INTEGER NOT NULL,
      first_position INTEGER,
      rank_position INTEGER,
      match_type TEXT NOT NULL,
      FOREIGN KEY (run_id) REFERENCES runs(run_id),
      UNIQUE(run_id, intent_id, model_provider, model_name, normalized_name)
  );
  ```
  - [x 2025-11-02 commit 2a474ea] Completed with UNIQUE constraint and foreign key

- [x] **Create indexes:**
  ```sql
  CREATE INDEX IF NOT EXISTS idx_mentions_timestamp ON mentions(timestamp_utc);
  CREATE INDEX IF NOT EXISTS idx_mentions_intent ON mentions(intent_id);
  CREATE INDEX IF NOT EXISTS idx_mentions_brand ON mentions(normalized_name);
  CREATE INDEX IF NOT EXISTS idx_mentions_mine ON mentions(is_mine);
  CREATE INDEX IF NOT EXISTS idx_mentions_rank ON mentions(rank_position);
  CREATE INDEX IF NOT EXISTS idx_answers_timestamp ON answers_raw(timestamp_utc);
  ```
  - [x 2025-11-02 commit 2a474ea] Completed all indexes for query optimization

#### 1.5.2 Database Operations

- [x] **Implement `insert_run(conn, run_id, timestamp_utc, total_intents, total_models)`**
  - [x] Use parameterized query (prevent SQL injection)
  - [x] Handle UNIQUE constraint (idempotent)
  - [x] Commit transaction
  - [x 2025-11-02 commit 22fc014] Completed with parameterized queries and error handling

- [x] **Implement `insert_answer_raw(conn, ...)`**
  - [x] Insert into answers_raw table
  - [x] Use parameterized query
  - [x] Handle UNIQUE constraint
  - [x] Store usage_meta as JSON string
  - [x 2025-11-02 commit 22fc014] Completed with parameterized queries and JSON serialization

- [x] **Implement `insert_mention(conn, ...)`**
  - [x] Insert into mentions table
  - [x] Use parameterized query
  - [x] Handle UNIQUE constraint
  - [x] Store is_mine as 1 or 0
  - [x 2025-11-02 commit 22fc014] Completed with parameterized queries and boolean conversion

- [x] **Implement `update_run_cost(conn, run_id, total_cost)`**
  - [x] Update runs table with final cost
  - [x] Use parameterized query
  - [x 2025-11-02 commit 22fc014] Completed with parameterized query

### 1.6 Storage Module - Migrations (storage/migrations.py)

- [x] **Create migration framework:**
  - [x] `CURRENT_SCHEMA_VERSION = 1` constant

  - [x] `get_current_version(conn) -> int` (implemented as `get_schema_version()` in db.py)
    - Query schema_version table
    - Return max version or 0 if empty

  - [x] `apply_migrations(conn, from_version: int)` (implemented in db.py)
    - Apply all migrations from from_version to CURRENT
    - Call migration functions in order
    - Insert version record after each migration
    - Commit transactions

  - [x] `migration_1(conn)` (implemented as `_migrate_to_v1()` in db.py)
    - Initial schema (already created by init_db)
    - Record version 1 application

  - [x 2025-11-02] Completed in db.py (lines 34, 109, 139, 218) - migrations framework integrated into db.py rather than separate migrations.py file

### 1.7 Testing - Milestone 1

- [x] **Test config/loader.py:**
  - [x] Test loading valid config file
  - [x] Test FileNotFoundError for missing file
  - [x] Test ValidationError for invalid YAML structure
  - [x] Test ValidationError for duplicate intent IDs
  - [x] Test ValidationError for empty brand aliases
  - [x] Test ValueError for missing env var
  - [x] Test ValueError for empty API key in env
  - [x] Test all Pydantic validators fire correctly
  - [x] Use pytest fixtures for temp config files
  - [x] Mock os.environ for API key resolution
  - [x 2025-11-02 commit af58993] Completed with 97% coverage for config module (schema.py and loader.py)

- [x] **Test utils/time.py:**
  - [x] Test utc_now() returns UTC datetime
  - [x] Test utc_timestamp() format is correct
  - [x] Test run_id_from_timestamp() format
  - [x] Test parse_timestamp() with valid input
  - [x] Test parse_timestamp() raises on missing 'Z'
  - [x] Test parse_timestamp() raises on invalid format
  - [x] Use freezegun to mock time
  - [x 2025-11-02 commit bcb3a9c] Completed with 100% coverage for utils/time.py

- [x] **Test storage/db.py:**
  - [x] Test init_db_if_needed() creates tables
  - [x] Test schema_version table created
  - [x] Test insert_run() with new run_id
  - [x] Test insert_run() idempotent (duplicate run_id)
  - [x] Test insert_answer_raw() with all fields
  - [x] Test UNIQUE constraint on answers_raw
  - [x] Test insert_mention() with all fields
  - [x] Test UNIQUE constraint on mentions
  - [x] Test update_run_cost() updates correctly
  - [x] Test indexes exist
  - [x] Use temp database for tests (tmp_path fixture)
  - [x 2025-11-02 commit fcfdc2e] Completed with 100% coverage for storage/db.py

- [x] **Test storage/migrations.py:**
  - [x] Test get_current_version() on empty DB
  - [x] Test get_current_version() on initialized DB
  - [x] Test apply_migrations() from version 0 to 1
  - [x] Test schema_version table populated after migration
  - [x 2025-11-02 commit fcfdc2e] Completed with comprehensive migration tests in test_storage_db.py (9 total migration tests including edge cases)

### 1.8 Milestone 1 Deliverable Checklist

- [ ] Config can be loaded from YAML
- [ ] Pydantic validation catches all error cases
- [ ] API keys resolved from environment variables
- [ ] Clear error messages for missing keys
- [ ] SQLite database initialized with schema
- [ ] All tables and indexes created
- [ ] Schema versioning working
- [ ] UTC timestamps enforced everywhere
- [ ] Tests pass with good coverage (aim for 80%+)
- [ ] Developer agent implemented code
- [ ] Tester agent wrote comprehensive tests
- [ ] Reviewer agent validated implementation

---

## Milestone 2: Provider Client + Runner Core

**Goal:** Running `runner.run_all()` in a REPL produces JSON + SQLite rows in output/ with cost estimates.

### 2.1 LLM Runner Module - Models (llm_runner/models.py)

- [x] **Define `LLMClient` Protocol:**
  ```python
  from typing import Protocol

  class LLMClient(Protocol):
      def generate_answer(self, prompt: str) -> tuple[str, dict]:
          """
          Run the model on the prompt and return (answer_text, usage_meta).
          Automatically retries on transient failures.
          Raises RuntimeError on permanent failures.
          """
  ```

- [x] **Implement `build_client(provider: str, model_name: str, api_key: str) -> LLMClient`**
  - [x] Check provider in supported list
  - [x] If provider == "openai", return OpenAIClient instance
  - [x] If provider == "anthropic", raise NotImplementedError (stub for future)
  - [x] Raise ValueError for unsupported provider
  - [x] Add comprehensive docstring
  - [x 2025-11-02 commit d76941a] Completed with LLMClient Protocol and build_client() factory implementation

### 2.2 LLM Runner Module - Retry Config (llm_runner/retry_config.py)

- [ ] **Define retry configuration constants:**
  - [ ] `MAX_ATTEMPTS = 3`
  - [ ] `MIN_WAIT_SECONDS = 1`
  - [ ] `MAX_WAIT_SECONDS = 10`
  - [ ] `RETRY_STATUS_CODES = [429, 500, 502, 503, 504]`
  - [ ] `NO_RETRY_STATUS_CODES = [401, 400, 404]`
  - [ ] `REQUEST_TIMEOUT = 30.0`

- [ ] **Create tenacity retry decorator configuration:**
  - [ ] Use `stop_after_attempt(MAX_ATTEMPTS)`
  - [ ] Use `wait_exponential(multiplier=1, min=MIN_WAIT, max=MAX_WAIT)`
  - [ ] Use `retry_if_exception_type((httpx.HTTPStatusError,))`
  - [ ] Add custom retry condition for specific status codes

### 2.3 LLM Runner Module - OpenAI Client (llm_runner/openai_client.py)

- [x] **Implement `OpenAIClient` class:**
  - [x 2025-11-02 commit 86ead9e] Completed with OpenAIClient class, retry logic, cost tracking, and error handling
  - [x] `__init__(self, model_name: str, api_key: str)`
    - Store model_name and api_key
    - Create httpx.Client with timeout=30.0

  - [x] `@retry(...)` decorator with tenacity config

  - [x] `generate_answer(self, prompt: str) -> tuple[str, dict]`
    - [x] Build chat completion request:
      - System message: "You are an unbiased market analyst. Provide factual, balanced recommendations."
      - User message: prompt
    - [x] Make POST request to OpenAI chat completions endpoint
    - [x] Set Authorization header with Bearer token
    - [x] Handle non-retry status codes (401, 400, 404)
      - Raise immediately without retry
    - [x] Handle retry status codes (429, 500+)
      - Let tenacity handle retry
    - [x] Extract answer text from response
    - [x] Extract usage metadata (prompt_tokens, completion_tokens, etc.)
    - [x] Log success with context (no API key in logs)
    - [x] On final failure, raise RuntimeError with descriptive message
    - [x] Include request_id in error if available
    - [x] Return (answer_text, usage_meta)

  - [x] `close(self)`
    - Close httpx client

- [x] **Add comprehensive docstrings to all methods**

### 2.4 Utils Module - Cost Estimation (utils/cost.py)

- [x] **Define pricing table:**
  ```python
  PRICING = {
      "openai": {
          "gpt-4o-mini": {"input": 0.150 / 1_000_000, "output": 0.600 / 1_000_000},
          "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
          "gpt-4-turbo": {"input": 10.00 / 1_000_000, "output": 30.00 / 1_000_000},
      },
      "anthropic": {
          "claude-3-5-haiku-20241022": {"input": 0.80 / 1_000_000, "output": 4.00 / 1_000_000},
          "claude-3-5-sonnet-20241022": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
      },
      # Updated: 2025-11-01
  }
  ```

- [x] **Implement `estimate_cost(provider: str, model: str, usage_meta: dict) -> float`**
  - [x] Get pricing for provider/model from PRICING table
  - [x] Return 0.0 with warning if pricing unavailable
  - [x] Extract prompt_tokens and completion_tokens from usage_meta
  - [x] Calculate: (input_tokens * input_price) + (output_tokens * output_price)
  - [x] Round to 6 decimal places
  - [x] Return cost in USD
  - [x] Add comprehensive docstring with disclaimer

- [x] **Add pricing update reminder in comments:**
  - [x] Note that pricing should be updated periodically
  - [x] Link to provider pricing pages
  - [x 2025-11-02 commit d76941a] Completed with pricing table and estimate_cost() implementation

### 2.5 Extractor Module - Mention Detector (extractor/mention_detector.py)

- [x] **Define `Mention` dataclass:**
  - Fields: `brand_name: str`, `normalized_name: str`, `first_position: int`, `match_type: str`
  - [x 2025-11-02 commit 83fa4a3] Completed with implementation

- [x] **Implement helper functions:**
  - [x] `normalize_brand_name(name: str) -> str`
    - Lowercase
    - Strip punctuation
    - Collapse whitespace
    - Return normalized form

  - [x] `create_word_boundary_pattern(alias: str) -> re.Pattern`
    - Escape special regex characters with `re.escape()`
    - Wrap with word boundaries: `\b{escaped}\b`
    - Compile with `re.IGNORECASE`
    - Return pattern

- [x] **Implement `detect_exact_mentions(text: str, brand_aliases: list[str]) -> list[Mention]`**
  - [x] For each brand alias:
    - Create word-boundary regex pattern
    - Search for matches in text
    - Record first occurrence position
    - Store original brand name and normalized name
    - Mark match_type as "exact"
  - [x] Deduplicate by normalized name (keep earliest)
  - [x] Return list of Mention objects

- [x] **Implement `detect_fuzzy_mentions(text: str, brand_aliases: list[str], threshold: float = 0.9) -> list[Mention]`**
  - [x] Import rapidfuzz.fuzz
  - [x] For each brand alias not found by exact match:
    - Use rapidfuzz to find similar strings in text
    - Check similarity score >= threshold
    - Record match position
    - Mark match_type as "fuzzy"
  - [x] Return list of Mention objects

- [x] **Implement `detect_mentions(text: str, my_brands: list[str], competitor_brands: list[str], fuzzy: bool = False) -> tuple[list[Mention], list[Mention]]`**
  - [x] Detect exact mentions for my_brands
  - [x] Detect exact mentions for competitor_brands
  - [x] If fuzzy=True:
    - Detect fuzzy mentions for brands not found exactly
  - [x] Sort mentions by first_position
  - [x] Return (my_mentions, competitor_mentions)
  - [x 2025-11-02 commit 83fa4a3] Completed with word-boundary regex and fuzzy matching implementation

### 2.6 Extractor Module - Rank Extractor (extractor/rank_extractor.py)

- [x] **Define `RankedBrand` dataclass:**
  - Fields: `brand_name: str`, `rank_position: int`, `confidence: float`

- [x] **Implement pattern-based extraction:**
  - [x] `extract_ranked_list_pattern(text: str, known_brands: list[str]) -> tuple[list[RankedBrand], float]`
    - [x] Look for numbered lists: `1. ToolName`, `2. ToolName`
    - [x] Look for bullet lists: `- ToolName`, `• ToolName`
    - [x] Look for markdown headers: `## ToolName`
    - [x] Extract tool names after markers
    - [x] Match against known_brands with fuzzy matching
    - [x] Assign rank_position based on order (0 = top)
    - [x] Calculate confidence:
      - 1.0: clear numbered list
      - 0.8: bullet list with consistent structure
      - 0.5: inferred from mention order
      - 0.3: no clear structure
    - [x] Deduplicate in first-seen order
    - [x] Return (ranked_list, confidence)

- [x] **Implement LLM-assisted extraction (stub for v1):**
  - [x] `extract_ranked_list_llm(text: str, known_brands: list[str], client: LLMClient) -> tuple[list[RankedBrand], float]`
    - [x] Build extraction prompt
    - [x] Call LLM with structured extraction request
    - [x] Parse JSON response
    - [x] Match against known_brands
    - [x] Return (ranked_list, 0.95) for high confidence
    - [x] Fallback to pattern-based if LLM call fails
    - [x] Note: This is optional and disabled by default in v1
  - [x 2025-11-02 commit b0ef4f3] Completed with stub implementation that falls back to pattern-based extraction

### 2.7 Extractor Module - Parser (extractor/parser.py)

- [x] **Define `ExtractionResult` dataclass:**
  - Fields:
    - `intent_id: str`
    - `model_provider: str`
    - `model_name: str`
    - `timestamp_utc: str`
    - `appeared_mine: bool`
    - `my_mentions: list[Mention]`
    - `competitor_mentions: list[Mention]`
    - `ranked_list: list[RankedBrand]`
    - `rank_extraction_method: str`
    - `rank_confidence: float`
  - [x 2025-11-02 commit 085f8ee] Completed with validation and comprehensive field definitions

- [x] **Implement `parse_answer(answer_text: str, brands: Brands, intent_id: str, provider: str, model_name: str, timestamp_utc: str, use_llm_extraction: bool = False) -> ExtractionResult`**
  - [x] Call detect_mentions() to get my_mentions and competitor_mentions
  - [x] Set appeared_mine = len(my_mentions) > 0
  - [x] Combine my_brands + competitor_brands for ranking
  - [x] Call extract_ranked_list_pattern() to get ranked list
  - [x] If use_llm_extraction=True (future):
    - Call extract_ranked_list_llm() instead
  - [x] Build ExtractionResult with all fields
  - [x] Return result
  - [x 2025-11-02 commit 085f8ee] Completed with 4-step pipeline, LLM extraction support, and error handling

### 2.8 Storage Module - Layout (storage/layout.py)

- [ ] **Define naming conventions:**
  - [ ] `get_run_directory(output_dir: str, run_id: str) -> str`
    - Return `{output_dir}/{run_id}/`

  - [ ] `get_raw_answer_filename(intent_id: str, provider: str, model: str) -> str`
    - Return `intent_{intent_id}_raw_{provider}_{model}.json`

  - [ ] `get_parsed_answer_filename(intent_id: str, provider: str, model: str) -> str`
    - Return `intent_{intent_id}_parsed_{provider}_{model}.json`

  - [ ] `get_error_filename(intent_id: str, provider: str, model: str) -> str`
    - Return `intent_{intent_id}_error_{provider}_{model}.json`

  - [ ] `get_run_meta_filename() -> str`
    - Return `run_meta.json`

  - [ ] `get_report_filename() -> str`
    - Return `report.html`

### 2.9 Storage Module - Writer (storage/writer.py)

- [ ] **Implement file writing utilities:**
  - [ ] `create_run_directory(output_dir: str, run_id: str) -> str`
    - Create directory with proper permissions
    - Return full path
    - Handle permission errors gracefully

  - [ ] `write_json(filepath: str, data: dict | list)`
    - Serialize to JSON with indent=2, ensure_ascii=False
    - Write UTF-8 encoded file
    - Handle disk full errors

  - [ ] `write_raw_answer(run_dir: str, intent_id: str, provider: str, model: str, data: dict)`
    - Build filename from layout conventions
    - Call write_json()

  - [ ] `write_parsed_answer(run_dir: str, intent_id: str, provider: str, model: str, data: dict)`
    - Build filename from layout conventions
    - Call write_json()

  - [ ] `write_error(run_dir: str, intent_id: str, provider: str, model: str, error_message: str)`
    - Build filename from layout conventions
    - Write error JSON with timestamp and message

  - [ ] `write_run_meta(run_dir: str, meta: dict)`
    - Write run_meta.json

  - [ ] `write_report_html(run_dir: str, html: str)`
    - Write report.html

### 2.10 LLM Runner Module - Runner (llm_runner/runner.py)

- [ ] **Define `RawAnswerRecord` dataclass:**
  - Fields:
    - `intent_id: str`
    - `prompt: str`
    - `model_provider: str`
    - `model_name: str`
    - `timestamp_utc: str`
    - `answer_text: str`
    - `answer_length: int`
    - `usage_meta: dict`
    - `estimated_cost_usd: float`

- [ ] **Implement `run_all(config: RuntimeConfig) -> dict`**
  - [ ] Generate run_id using utils.time.run_id_from_timestamp()
  - [ ] Create run directory using storage.writer
  - [ ] Open SQLite connection
  - [ ] Insert run record into database
  - [ ] Initialize cost accumulator
  - [ ] Initialize results list
  - [ ] Loop over all (intent, model) combinations:
    - [ ] Build LLM client using llm_runner.models.build_client()
    - [ ] Try to generate answer:
      - [ ] Call client.generate_answer(intent.prompt)
      - [ ] Get timestamp_utc
      - [ ] Build RawAnswerRecord
      - [ ] Estimate cost using utils.cost.estimate_cost()
      - [ ] Call extractor.parser.parse_answer()
      - [ ] Write raw answer JSON
      - [ ] Write parsed answer JSON
      - [ ] Insert into answers_raw table
      - [ ] Insert mentions into mentions table
      - [ ] Accumulate cost
      - [ ] Log success
    - [ ] Catch exceptions:
      - [ ] Log error (no API key in logs)
      - [ ] Write error JSON
      - [ ] Continue to next query
  - [ ] Update run record with total cost
  - [ ] Close SQLite connection
  - [ ] Return summary dict:
    ```python
    {
        "run_id": run_id,
        "output_dir": run_dir,
        "total_cost_usd": total_cost,
        "successful_queries": success_count,
        "total_queries": total_count
    }
    ```

### 2.11 Testing - Milestone 2

- [ ] **Test llm_runner/models.py:**
  - [ ] Test build_client() with "openai" provider
  - [ ] Test build_client() raises for "anthropic" (not implemented)
  - [ ] Test build_client() raises for unknown provider

- [ ] **Test llm_runner/openai_client.py:**
  - [ ] Use pytest-httpx to mock HTTP responses
  - [ ] Test successful API call
  - [ ] Test retry on 429 (rate limit)
  - [ ] Test retry on 500 (server error)
  - [ ] Test retry on 503 (service unavailable)
  - [ ] Test no retry on 401 (auth error)
  - [ ] Test no retry on 400 (bad request)
  - [ ] Test max retries exceeded
  - [ ] Test timeout handling
  - [ ] Test response parsing
  - [ ] Test usage metadata extraction
  - [ ] Verify API key never logged

- [ ] **Test utils/cost.py:**
  - [ ] Test estimate_cost() with known pricing
  - [ ] Test estimate_cost() with unknown model (returns 0.0)
  - [ ] Test cost calculation accuracy
  - [ ] Test rounding to 6 decimals

- [ ] **Test extractor/mention_detector.py:**
  - [ ] Test normalize_brand_name()
  - [ ] Test create_word_boundary_pattern()
  - [ ] Test detect_exact_mentions() finds brands
  - [ ] Test word boundary prevents false positives ("hub" not in "GitHub")
  - [ ] Test case-insensitive matching
  - [ ] Test fuzzy matching with rapidfuzz
  - [ ] Test fuzzy threshold (90%)
  - [ ] Test deduplication by normalized name
  - [ ] Test first_position tracking

- [ ] **Test extractor/rank_extractor.py:**
  - [ ] Test pattern extraction with numbered list
  - [ ] Test pattern extraction with bullets
  - [ ] Test pattern extraction with markdown headers
  - [ ] Test confidence calculation
  - [ ] Test matching against known brands
  - [ ] Test deduplication
  - [ ] Test rank_position assignment

- [ ] **Test extractor/parser.py:**
  - [ ] Test parse_answer() with sample LLM response
  - [ ] Test appeared_mine flag
  - [ ] Test my_mentions populated
  - [ ] Test competitor_mentions populated
  - [ ] Test ranked_list extraction
  - [ ] Use fixtures for sample answers

- [ ] **Test storage/writer.py:**
  - [ ] Test create_run_directory()
  - [ ] Test write_json() with dict
  - [ ] Test write_json() with list
  - [ ] Test UTF-8 encoding
  - [ ] Test write_raw_answer()
  - [ ] Test write_parsed_answer()
  - [ ] Test write_error()
  - [ ] Use tmp_path fixture

- [ ] **Test llm_runner/runner.py:**
  - [ ] Mock LLM client responses
  - [ ] Test run_all() end-to-end
  - [ ] Test run_id generation
  - [ ] Test directory creation
  - [ ] Test database inserts
  - [ ] Test JSON file creation
  - [ ] Test cost accumulation
  - [ ] Test error handling (API failure)
  - [ ] Test partial success (some queries fail)
  - [ ] Verify error JSON written on failure
  - [ ] Use temp database and output directory

### 2.12 Milestone 2 Deliverable Checklist

- [ ] LLM client interface defined
- [ ] OpenAI client implemented with retry logic
- [ ] Retry works correctly (429, 500+ status codes)
- [ ] Cost estimation working
- [ ] Mention detection with word boundaries
- [ ] Fuzzy matching with rapidfuzz
- [ ] Rank extraction with pattern matching
- [ ] Parser orchestrates mention + rank extraction
- [ ] Runner orchestrates full execution
- [ ] JSON artifacts written correctly
- [ ] SQLite inserts working
- [ ] Costs calculated and tracked
- [ ] Error handling robust (queries can fail gracefully)
- [ ] Tests pass with 80%+ coverage
- [ ] HTTP mocking working in tests
- [ ] Developer agent implemented code
- [ ] Tester agent wrote comprehensive tests
- [ ] Reviewer agent validated implementation

---

## Milestone 3: Report Generation + CLI

**Goal:** User can run CLI in both human and agent modes, see beautiful output or structured JSON, and get correct exit codes.

### 3.1 Utils Module - Console (utils/console.py)

- [ ] **Setup Rich console infrastructure:**
  - [ ] Import Rich components (Console, Progress, Table, Panel, Status)
  - [ ] Create global console instance

- [ ] **Implement `OutputMode` class:**
  - [ ] `__init__(self, format: str = "text", quiet: bool = False)`
  - [ ] `is_human(self) -> bool`
  - [ ] `is_agent(self) -> bool`
  - [ ] `add_json(self, key: str, value: Any)`
  - [ ] `flush_json(self)`
  - [ ] Create global output_mode instance

- [ ] **Implement context managers and helpers:**
  - [ ] `@contextmanager spinner(message: str)`
    - Show spinner in human mode
    - Silent in agent mode

  - [ ] `create_progress_bar() -> Progress`
    - Return Rich Progress in human mode
    - Return NoOpProgress in agent mode

  - [ ] `NoOpProgress` class
    - Implement __enter__, __exit__
    - Implement add_task(), advance() as no-ops

- [ ] **Implement output functions:**
  - [ ] `success(message: str)`
    - Rich green checkmark in human mode
    - Buffer JSON in agent mode

  - [ ] `error(message: str)`
    - Rich red X in human mode
    - Buffer JSON in agent mode

  - [ ] `warning(message: str)`
    - Rich yellow warning in human mode
    - Buffer JSON in agent mode

  - [ ] `info(message: str)`
    - Rich blue info in human mode
    - Silent in agent/quiet mode

- [ ] **Implement `print_summary_table(results: list[dict])`**
  - [ ] In human mode:
    - Create Rich Table with rounded borders
    - Columns: Intent, Model, Appeared, Cost, Status
    - Color-code: green for success, red for failure
  - [ ] In agent mode:
    - Buffer results as JSON array
  - [ ] In quiet mode:
    - Skip output

- [ ] **Implement `print_banner(version: str)`**
  - [ ] Show fancy ASCII art banner in human mode
  - [ ] Silent in agent mode

- [ ] **Implement `print_final_summary(run_id, output_dir, total_cost, successful, total)`**
  - [ ] In human mode:
    - Create Rich Panel with stats
    - Show run_id, output_dir, cost, query counts
    - Green border if all successful, yellow if partial
  - [ ] In agent mode:
    - Buffer all fields as JSON
    - Flush JSON to stdout
  - [ ] In quiet mode:
    - Print tab-separated values

### 3.2 Report Module - Cost Formatter (report/cost_formatter.py)

- [ ] **Implement cost formatting utilities:**
  - [ ] `format_cost_usd(cost: float) -> str`
    - Format to 4 decimal places with $ prefix
    - Example: "$0.0023"

  - [ ] `format_cost_summary(costs: list[float]) -> dict`
    - Calculate total, min, max, average
    - Return dict with formatted strings

### 3.3 Report Module - Generator (report/generator.py)

- [ ] **Create Jinja2 template (report/templates/report.html.j2):**
  - [ ] HTML5 structure with inline CSS
  - [ ] Mobile-responsive design
  - [ ] Sections:
    - [ ] Header with run_id, timestamp, models used
    - [ ] Summary stats (total cost, queries, success rate)
    - [ ] For each intent:
      - [ ] Intent title and prompt
      - [ ] For each model:
        - [ ] Model name
        - [ ] "Appeared" indicator (green ✓ or red ✗)
        - [ ] My mentions (brand names + positions)
        - [ ] Competitor mentions (sorted by position)
        - [ ] Ranked list with confidence indicator
        - [ ] Query cost
    - [ ] Footer with cost disclaimer
  - [ ] Use Bootstrap-like responsive grid or simple flexbox
  - [ ] Color scheme: professional blues and greens
  - [ ] **CRITICAL: Ensure autoescaping enabled**

- [ ] **Implement `generate_report(run_dir: str, run_id: str, config: RuntimeConfig, results: list) -> str`**
  - [ ] Read all parsed JSON files from run_dir
  - [ ] Aggregate data for template
  - [ ] Setup Jinja2 environment:
    ```python
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=True  # CRITICAL for security
    )
    ```
  - [ ] Load template
  - [ ] Render with data
  - [ ] Return HTML string
  - [ ] Test with malicious brand name: `<script>alert('xss')</script>`

- [ ] **Implement `write_report(run_dir: str, config: RuntimeConfig, results: list)`**
  - [ ] Call generate_report()
  - [ ] Write HTML to report.html using storage.writer

### 3.4 CLI Module (cli.py)

- [ ] **Setup Typer app:**
  - [ ] Import Typer, Rich, and all modules
  - [ ] Create Typer app instance
  - [ ] Read VERSION file for version display

- [ ] **Define exit codes:**
  ```python
  EXIT_SUCCESS = 0          # All queries successful
  EXIT_CONFIG_ERROR = 1     # Config validation failed
  EXIT_DB_ERROR = 2         # Database initialization failed
  EXIT_PARTIAL_FAILURE = 3  # Some queries failed
  EXIT_COMPLETE_FAILURE = 4 # All queries failed
  ```

- [ ] **Implement `main()` entry point:**
  - [ ] Setup Typer app
  - [ ] Add callback for --version

- [ ] **Implement `run` command:**
  ```python
  @app.command()
  def run(
      config: Path = typer.Option(..., "--config", help="Path to watcher.config.yaml"),
      format: str = typer.Option("text", "--format", help="Output format: text or json"),
      quiet: bool = typer.Option(False, "--quiet", help="Minimal output"),
      yes: bool = typer.Option(False, "--yes", help="Skip all prompts"),
      verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
  ):
  ```
  - [ ] Set output_mode based on flags
  - [ ] Setup logging level (DEBUG if verbose)
  - [ ] Show banner in human mode
  - [ ] Wrap operations in try/except blocks:
    - [ ] Load config (catch errors → EXIT_CONFIG_ERROR)
    - [ ] Init database (catch errors → EXIT_DB_ERROR)
    - [ ] Show spinner "Loading config..." in human mode
    - [ ] Success message after config load
    - [ ] If not --yes, confirm intent count and model count
    - [ ] Estimate rough cost and show warning if high
    - [ ] Create progress bar in human mode
    - [ ] Call runner.run_all()
    - [ ] Update progress bar for each query
    - [ ] Generate report
    - [ ] Write report HTML
    - [ ] Show summary table
    - [ ] Show final summary panel/JSON
    - [ ] Determine exit code:
      - 0 if all successful
      - 3 if partial failure
      - 4 if complete failure
    - [ ] Exit with appropriate code

- [ ] **Implement `validate` command:**
  ```python
  @app.command()
  def validate(
      config: Path = typer.Option(..., "--config", help="Path to watcher.config.yaml"),
      format: str = typer.Option("text", "--format", help="Output format: text or json"),
  ):
  ```
  - [ ] Set output_mode
  - [ ] Try to load config
  - [ ] Validate all Pydantic models
  - [ ] Check if API key env vars are set (without reading values)
  - [ ] Output success or error
  - [ ] Return EXIT_SUCCESS or EXIT_CONFIG_ERROR

- [ ] **Implement `version` callback:**
  - [ ] Read VERSION file
  - [ ] Print version string
  - [ ] Exit

- [ ] **Write comprehensive --help text:**
  - [ ] Command description
  - [ ] Option explanations
  - [ ] Usage examples:
    ```
    # Human mode (default)
    llm-answer-watcher run --config watcher.config.yaml

    # Agent mode (structured JSON output)
    llm-answer-watcher run --config watcher.config.yaml --format json

    # Quiet mode (minimal output)
    llm-answer-watcher run --config watcher.config.yaml --quiet

    # Automation mode (no prompts)
    llm-answer-watcher run --config watcher.config.yaml --yes --format json

    # Validate config before running
    llm-answer-watcher validate --config watcher.config.yaml
    ```
  - [ ] Exit code documentation:
    ```
    Exit Codes:
      0: Success - all queries completed successfully
      1: Configuration error (invalid YAML, missing API keys)
      2: Database error (cannot create or access SQLite)
      3: Partial failure (some queries failed, but run completed)
      4: Complete failure (no queries succeeded)
    ```

### 3.5 Example Configuration

- [ ] **Create examples/ directory**
- [ ] **Create examples/watcher.config.yaml:**
  - [ ] Example with 2-3 intents
  - [ ] Example brands (mine and competitors)
  - [ ] Multiple models (gpt-4o-mini, gpt-4o)
  - [ ] Comments explaining each section
  - [ ] Use env var placeholders (no real API keys)

- [ ] **Create examples/.env.example:**
  - [ ] Show required environment variables
  - [ ] OPENAI_API_KEY=your_key_here
  - [ ] Instructions for setting up

### 3.6 Testing - Milestone 3

- [ ] **Test utils/console.py:**
  - [ ] Test OutputMode class
  - [ ] Test is_human() and is_agent()
  - [ ] Test spinner() context manager
  - [ ] Test progress bar creation
  - [ ] Test NoOpProgress behavior
  - [ ] Test success/error/warning/info functions
  - [ ] Test print_summary_table() in both modes
  - [ ] Test print_final_summary() in both modes
  - [ ] Test JSON buffering and flushing
  - [ ] Capture stdout to verify output

- [ ] **Test report/generator.py:**
  - [ ] Test generate_report() with sample data
  - [ ] Test HTML structure is valid
  - [ ] Test autoescaping prevents XSS
  - [ ] Test with malicious input: `<script>alert('xss')</script>`
  - [ ] Verify brand names are escaped in output
  - [ ] Test mobile-responsive CSS
  - [ ] Test cost display
  - [ ] Test confidence indicators
  - [ ] Snapshot test for HTML output

- [ ] **Test cli.py:**
  - [ ] Use Typer testing utilities
  - [ ] Test run command with valid config
  - [ ] Test run command with invalid config (exit code 1)
  - [ ] Test run command with missing env vars (exit code 1)
  - [ ] Test run command with --format json
  - [ ] Test JSON output has no ANSI codes
  - [ ] Test JSON output is valid (parse with json.loads())
  - [ ] Test run command with --quiet
  - [ ] Test run command with --yes (no prompts)
  - [ ] Test validate command with valid config
  - [ ] Test validate command with invalid config
  - [ ] Test --version flag
  - [ ] Test exit codes are correct
  - [ ] Mock runner.run_all() for isolation

### 3.7 Milestone 3 Deliverable Checklist

- [ ] Rich console utilities implemented
- [ ] OutputMode pattern working
- [ ] Spinners and progress bars in human mode
- [ ] Tables and panels in human mode
- [ ] JSON output in agent mode (no ANSI codes)
- [ ] Quiet mode for minimal output
- [ ] Report template created with inline CSS
- [ ] Report generator working with autoescaping
- [ ] XSS prevention tested
- [ ] CLI commands implemented (run, validate)
- [ ] Exit codes correct (0-4)
- [ ] --help text comprehensive with examples
- [ ] Example config created
- [ ] User can run human mode and see beautiful output
- [ ] User can run agent mode and get valid JSON
- [ ] User can run quiet mode and get tab-separated values
- [ ] User can run --yes mode without prompts
- [ ] report.html opens in browser correctly
- [ ] Tests pass with 80%+ coverage
- [ ] Developer agent implemented code
- [ ] Tester agent wrote comprehensive tests
- [ ] Reviewer agent validated implementation

---

## Milestone 4: Polish, Docs, Tests

**Goal:** OSS v1 is production-ready and ready to publish.

### 4.1 Documentation

#### 4.1.1 README.md

- [ ] **Write comprehensive README.md:**
  - [ ] Project title and tagline
  - [ ] Badges (license, Python version, tests)
  - [ ] Quick description (1-2 sentences)
  - [ ] Key features list
  - [ ] Prerequisites:
    - Python 3.12+ or 3.13
    - uv (recommended) or pip
  - [ ] Installation:
    ```bash
    # With uv (recommended)
    uv sync

    # With pip
    pip install -e .
    ```
  - [ ] Configuration:
    - [ ] How to create watcher.config.yaml
    - [ ] Required sections explained
    - [ ] Environment variables for API keys
    - [ ] Best practices for brand aliases (avoid generic terms, use complete names)
  - [ ] Usage:
    - [ ] Human mode example
    - [ ] Agent mode example
    - [ ] Quiet mode example
    - [ ] Validation example
  - [ ] Output:
    - [ ] Where data is stored (output/, watcher.db)
    - [ ] What report.html contains
    - [ ] How to query SQLite for trends
  - [ ] Exit codes reference (0-4)
  - [ ] Cost estimation:
    - [ ] How it works
    - [ ] Disclaimer about accuracy
    - [ ] Link to provider pricing pages
  - [ ] Using with AI Agents:
    - [ ] Explain --format json flag
    - [ ] Explain --yes flag
    - [ ] Explain exit codes for automation
    - [ ] Example automation script
  - [ ] Security notes:
    - [ ] Never commit .env files
    - [ ] API keys loaded from environment only
  - [ ] Example queries for SQLite:
    ```sql
    -- Show all times we appeared in last 7 days
    SELECT * FROM mentions
    WHERE is_mine = 1 AND timestamp_utc > date('now', '-7 days')
    ORDER BY timestamp_utc DESC;

    -- Which competitor ranked #1 most often?
    SELECT normalized_name, COUNT(*) as times_ranked_first
    FROM mentions
    WHERE rank_position = 0 AND is_mine = 0
    GROUP BY normalized_name
    ORDER BY times_ranked_first DESC;

    -- Total LLM query cost this month
    SELECT SUM(total_cost_usd) FROM runs
    WHERE timestamp_utc >= date('now', 'start of month');
    ```
  - [ ] Contributing link
  - [ ] License
  - [ ] Acknowledgments

#### 4.1.2 CONTRIBUTING.md

- [ ] **Write contributor guide:**
  - [ ] Welcome message
  - [ ] Prerequisites (Python 3.12+, uv)
  - [ ] Setup:
    ```bash
    git clone <repo>
    cd llm-answer-watcher
    uv sync
    ```
  - [ ] Running tests:
    ```bash
    pytest
    pytest --cov  # with coverage
    pytest -v     # verbose
    ```
  - [ ] Code standards:
    - [ ] Python 3.12+ type hints (use `|` not `Union[]`)
    - [ ] Pydantic for validation
    - [ ] Docstrings on all public functions (Google style)
    - [ ] Word-boundary regex for brand matching
    - [ ] UTC timestamps everywhere
    - [ ] No API keys in logs
  - [ ] Testing guidelines:
    - [ ] Aim for 80%+ coverage
    - [ ] Use fixtures for common scenarios
    - [ ] Mock HTTP calls with pytest-httpx
    - [ ] Mock time with freezegun
    - [ ] Use temp files/databases for tests
  - [ ] How to add a new LLM provider:
    - [ ] Implement LLMClient protocol
    - [ ] Add to build_client() in llm_runner/models.py
    - [ ] Add pricing to utils/cost.py
    - [ ] Add tests
    - [ ] Update documentation
  - [ ] Pull request process:
    - [ ] Fork the repo
    - [ ] Create feature branch
    - [ ] Make changes with tests
    - [ ] Run linting and tests
    - [ ] Submit PR with description
  - [ ] Code review expectations
  - [ ] Subagent team workflow:
    - [ ] Developer implements
    - [ ] Tester writes tests
    - [ ] Reviewer validates
  - [ ] Questions? Open an issue

### 4.2 Expanded Test Coverage

#### 4.2.1 Config Tests

- [ ] **Test all validation edge cases:**
  - [ ] Empty config file
  - [ ] Missing required sections
  - [ ] Invalid YAML syntax
  - [ ] Duplicate intent IDs
  - [ ] Empty brand aliases
  - [ ] Generic brand terms (too short)
  - [ ] Invalid provider name
  - [ ] Missing API key env var
  - [ ] Empty API key in env var
  - [ ] Invalid output_dir path
  - [ ] Zero models configured
  - [ ] Zero intents configured
  - [ ] Brands in both mine and competitors lists

#### 4.2.2 Extractor Tests

- [ ] **Comprehensive mention detection tests:**
  - [ ] Exact match with word boundaries
  - [ ] Case-insensitive matching
  - [ ] Special characters in brand names
  - [ ] Multiple occurrences (track first position)
  - [ ] Fuzzy matching near-matches
  - [ ] Fuzzy threshold testing
  - [ ] Unicode characters in brand names
  - [ ] Very long brand names (>100 chars)
  - [ ] Empty text input
  - [ ] Text with no matches
  - [ ] Overlapping brand aliases

- [ ] **Comprehensive rank extraction tests:**
  - [ ] Numbered list (1. 2. 3.)
  - [ ] Numbered list with parentheses (1) 2) 3))
  - [ ] Bullet list with dashes (- Item)
  - [ ] Bullet list with dots (• Item)
  - [ ] Markdown headers (## Tool)
  - [ ] Mixed format (some numbered, some bullets)
  - [ ] Conversational answer (no clear structure)
  - [ ] Empty list
  - [ ] Confidence scoring accuracy
  - [ ] Brand name matching with fuzzy logic
  - [ ] Deduplication of repeated brands

#### 4.2.3 Database Tests

- [ ] **SQLite roundtrip tests:**
  - [ ] Create temp database
  - [ ] Insert run record
  - [ ] Insert answer_raw records
  - [ ] Insert mention records
  - [ ] Query back and verify data
  - [ ] Test UNIQUE constraints:
    - [ ] Duplicate run_id (should skip)
    - [ ] Duplicate (run_id, intent_id, provider, model) in answers_raw
    - [ ] Duplicate (run_id, intent_id, provider, model, normalized_name) in mentions
  - [ ] Test foreign key constraints
  - [ ] Test indexes exist and are used
  - [ ] Test update_run_cost()

#### 4.2.4 Report Tests

- [ ] **HTML generation tests:**
  - [ ] Generate report with sample data
  - [ ] Verify HTML structure (valid HTML5)
  - [ ] Verify autoescaping works
  - [ ] Test with XSS payloads:
    - `<script>alert('xss')</script>`
    - `<img src=x onerror=alert(1)>`
    - `<iframe src="javascript:alert(1)">`
  - [ ] Verify brand names are escaped
  - [ ] Verify intent prompts are escaped
  - [ ] Test with empty data (no queries)
  - [ ] Test with partial data (some queries failed)
  - [ ] Snapshot test for HTML output

#### 4.2.5 Cost Calculation Tests

- [ ] **Pricing accuracy tests:**
  - [ ] Test known model costs
  - [ ] Test unknown model (returns 0.0)
  - [ ] Test with zero tokens
  - [ ] Test with large token counts
  - [ ] Test rounding behavior
  - [ ] Test cost accumulation across queries

#### 4.2.6 Schema Migration Tests

- [ ] **Migration framework tests:**
  - [ ] Test get_current_version() on new DB (version 0)
  - [ ] Test apply_migrations() from 0 to 1
  - [ ] Test schema_version table populated correctly
  - [ ] Test migration idempotency (can run multiple times)
  - [ ] Test future migration (stub migration 2)

#### 4.2.7 Retry Logic Tests

- [ ] **Comprehensive retry tests:**
  - [ ] Mock 429 (rate limit) → retry → success
  - [ ] Mock 500 (server error) → retry → success
  - [ ] Mock 503 (service unavailable) → retry → success
  - [ ] Mock 429 → 429 → 429 → fail after max retries
  - [ ] Mock 401 (auth error) → fail immediately (no retry)
  - [ ] Mock 400 (bad request) → fail immediately (no retry)
  - [ ] Test exponential backoff timing
  - [ ] Test max wait time (10s)
  - [ ] Test timeout handling (30s)

#### 4.2.8 CLI Tests

- [ ] **End-to-end CLI tests:**
  - [ ] Test run command success
  - [ ] Test run command with config error
  - [ ] Test run command with DB error
  - [ ] Test run command with partial failures
  - [ ] Test run command with complete failure
  - [ ] Verify exit codes correct
  - [ ] Test --format json output
  - [ ] Verify JSON has no ANSI codes
  - [ ] Verify JSON is valid (parse it)
  - [ ] Verify JSON has required fields
  - [ ] Test --quiet output
  - [ ] Test --yes flag (no prompts)
  - [ ] Test validate command
  - [ ] Test --version flag

### 4.3 Coverage Target

- [ ] **Achieve 80%+ test coverage:**
  - [ ] Run pytest with coverage: `pytest --cov=llm_answer_watcher --cov-report=html`
  - [ ] Review coverage report
  - [ ] Add tests for uncovered lines
  - [ ] Target 100% coverage for critical paths:
    - config.loader
    - llm_runner.openai_client
    - extractor.mention_detector
    - storage.db
  - [ ] Document any intentionally uncovered code

### 4.4 CI/CD Pipeline

- [ ] **Create .github/workflows/test.yml:**
  - [ ] Trigger on push and pull requests
  - [ ] Test matrix: Python 3.12 and 3.13
  - [ ] Steps:
    - [ ] Checkout code
    - [ ] Setup Python
    - [ ] Install uv
    - [ ] Run `uv sync`
    - [ ] Run `pytest --cov`
    - [ ] Upload coverage to Codecov (optional)
  - [ ] Fail build if tests fail
  - [ ] Badge for README

- [ ] **Create .github/workflows/lint.yml:**
  - [ ] Trigger on push and pull requests
  - [ ] Steps:
    - [ ] Checkout code
    - [ ] Setup Python
    - [ ] Install ruff
    - [ ] Run `ruff check .`
    - [ ] Run `ruff format --check .`
  - [ ] Fail build if linting fails

### 4.5 Example Output

- [ ] **Create examples/sample_output/ directory**
- [ ] **Generate sample output:**
  - [ ] Run CLI with example config
  - [ ] Copy output directory to examples/sample_output/
  - [ ] Include:
    - [ ] run_meta.json (redact any sensitive info)
    - [ ] Sample intent_*_raw_*.json files
    - [ ] Sample intent_*_parsed_*.json files
    - [ ] report.html
  - [ ] Add README explaining the sample output

### 4.6 Final Polish

- [ ] **Review all code for quality:**
  - [ ] Use Reviewer agent to check each module
  - [ ] Ensure all docstrings present
  - [ ] Ensure all type hints present
  - [ ] Check for security issues
  - [ ] Check for performance issues
  - [ ] Verify error messages are helpful

- [ ] **Update all documentation:**
  - [ ] Verify README is accurate
  - [ ] Verify CONTRIBUTING is complete
  - [ ] Update SPECS.md if anything changed
  - [ ] Update AGENTS.md if workflow improved
  - [ ] Update HOOKS.md if hooks added

- [ ] **Verify git commits:**
  - [ ] All commits follow conventional format
  - [ ] No secrets in repo history
  - [ ] .gitignore covers all output files

### 4.7 Milestone 4 Deliverable Checklist

- [ ] README.md complete and accurate
- [ ] CONTRIBUTING.md clear and helpful
- [ ] Test coverage >= 80%
- [ ] Critical paths have 100% coverage
- [ ] CI/CD pipeline passing
- [ ] GitHub Actions running tests
- [ ] Example config in examples/
- [ ] Sample output in examples/sample_output/
- [ ] All docstrings present
- [ ] All type hints present
- [ ] Reviewer agent approved all code
- [ ] No security vulnerabilities
- [ ] No API keys in repo
- [ ] Exit codes working correctly
- [ ] --help text comprehensive
- [ ] Agent mode tested by AI agent
- [ ] Human mode tested manually
- [ ] report.html renders beautifully
- [ ] SQLite queries work as documented

---

## Definition of Done for OSS v1

**Before publishing, verify ALL these conditions:**

### Installation & Setup

- [ ] `pip install -e .` works on Python 3.12
- [ ] `pip install -e .` works on Python 3.13
- [ ] `uv sync` works on Python 3.12
- [ ] `uv sync` works on Python 3.13
- [ ] All dependencies install without errors
- [ ] Entry point `llm-answer-watcher` is available after install

### CLI Commands

- [ ] `llm-answer-watcher --version` prints version from VERSION file
- [ ] `llm-answer-watcher --help` shows comprehensive help text
- [ ] `llm-answer-watcher validate --config examples/watcher.config.yaml` passes
- [ ] `llm-answer-watcher validate --config examples/watcher.config.yaml --format json` produces valid JSON

### Human Mode (Default)

- [ ] `llm-answer-watcher run --config examples/watcher.config.yaml` completes successfully
- [ ] Shows startup banner
- [ ] Shows spinner "Loading config..."
- [ ] Shows confirmation prompt (can be skipped with --yes)
- [ ] Shows progress bar for queries
- [ ] Shows summary table with:
  - Intent names
  - Model names
  - Appeared indicators (✓ or ✗)
  - Costs
  - Status indicators
- [ ] Shows final summary panel with:
  - Run ID
  - Output directory
  - Total cost
  - Query success count
- [ ] Creates timestamped run folder under output/
- [ ] Writes run_meta.json with cost summary
- [ ] Writes intent_*_raw_*.json files
- [ ] Writes intent_*_parsed_*.json files
- [ ] Writes report.html
- [ ] Updates watcher.db with:
  - Row in runs table
  - Rows in answers_raw table
  - Rows in mentions table
  - Correct schema_version
- [ ] If model call fails after retries, writes *_error_*.json
- [ ] Returns exit code 0 on success
- [ ] Returns exit code 3 on partial failure

### Agent Mode (--format json)

- [ ] `llm-answer-watcher run --config examples/watcher.config.yaml --format json` produces valid JSON
- [ ] JSON output includes:
  - `run_id`
  - `output_dir`
  - `total_cost_usd`
  - `successful_queries`
  - `total_queries`
  - `results` array
- [ ] JSON output has NO ANSI color codes
- [ ] JSON output has NO progress indicators
- [ ] JSON can be parsed with `jq`
- [ ] Returns correct exit codes (0-4)
- [ ] Test automation script:
  ```bash
  output=$(llm-answer-watcher run --config test.yaml --format json)
  echo $output | jq .run_id
  # Should print run_id without errors
  ```

### Quiet Mode (--quiet)

- [ ] `llm-answer-watcher run --config examples/watcher.config.yaml --quiet` produces minimal output
- [ ] Output is tab-separated values
- [ ] No spinners or progress bars
- [ ] No Rich formatting

### Automation Mode (--yes)

- [ ] `llm-answer-watcher run --config examples/watcher.config.yaml --yes` skips all prompts
- [ ] Runs without user interaction
- [ ] Can be used in scripts

### Report HTML

- [ ] report.html opens in browser without errors
- [ ] Shows:
  - Run ID and timestamp
  - Models used
  - Summary stats (total cost, queries, success rate)
  - For each intent:
    - Intent title and prompt
    - For each model:
      - Model name
      - Appeared indicator (✓ Yes or ✗ No)
      - My mentions (brand names + positions)
      - Competitor mentions (sorted by position)
      - Ranked list with confidence indicator
      - Query cost
  - Cost disclaimer in footer
- [ ] HTML is valid HTML5
- [ ] CSS is inline (no external dependencies)
- [ ] Mobile-responsive layout
- [ ] Brand names are properly escaped (no XSS)
- [ ] Match types shown (exact vs fuzzy)

### Database

- [ ] watcher.db created at configured path
- [ ] Schema version = 1
- [ ] Tables exist: schema_version, runs, answers_raw, mentions
- [ ] Indexes exist and are used
- [ ] UNIQUE constraints prevent duplicates
- [ ] Foreign keys enforced
- [ ] Can query with sqlite3:
  ```bash
  sqlite3 output/watcher.db "SELECT * FROM runs ORDER BY timestamp_utc DESC LIMIT 5;"
  # Shows recent runs
  ```

### Core Features

- [ ] Retry logic works (tested with mocked 429/500)
- [ ] Cost estimates calculated and displayed
- [ ] Word-boundary matching prevents false positives
- [ ] Fuzzy matching catches variations
- [ ] Rank extraction with confidence scores
- [ ] Exit codes correct based on run outcome
- [ ] Rich output works in human mode
- [ ] JSON output works in agent mode
- [ ] Timestamps are UTC with 'Z' suffix
- [ ] API keys never logged
- [ ] API keys never persisted to disk

### Documentation

- [ ] README documents:
  - Setup with uv
  - Config format
  - How to add intents and brands
  - Best practices for brand aliases
  - Where data is stored
  - How to query SQLite
  - Cost estimation disclaimer
  - Security notes (never commit .env)
  - Using with AI agents section
- [ ] CONTRIBUTING documents:
  - Code style
  - Docstrings required
  - Testing guidelines
  - How to add new LLM providers
- [ ] LICENSE is present (MIT)
- [ ] SPECS.md is accurate and up-to-date
- [ ] AGENTS.md documents subagent team
- [ ] HOOKS.md documents hooks

### Testing

- [ ] Tests pass: `pytest`
- [ ] Coverage >= 80%: `pytest --cov`
- [ ] Critical paths have 100% coverage
- [ ] All validators tested
- [ ] Retry logic tested
- [ ] HTTP mocking working
- [ ] Time mocking working
- [ ] Temp files/DBs used in tests
- [ ] XSS prevention tested

### CI/CD

- [ ] GitHub Actions workflow runs on PRs
- [ ] Tests run on Python 3.12 and 3.13
- [ ] Linting runs with ruff
- [ ] Builds pass

### Security

- [ ] No secrets in repo
- [ ] .env files gitignored
- [ ] Example configs use env var placeholders
- [ ] API keys never logged
- [ ] SQL injection prevented (parameterized queries)
- [ ] XSS prevented (Jinja2 autoescaping)

---

## Post-v1 Enhancements (Future)

These tasks are NOT required for v1 but are documented for future reference:

### Future Milestone: Additional LLM Providers

- [ ] Implement Anthropic client (anthropic_client.py)
- [ ] Add pricing for Claude models
- [ ] Test Anthropic retry logic
- [ ] Update docs with Anthropic setup

### Future Milestone: LLM-Assisted Rank Extraction

- [ ] Implement extract_ranked_list_llm() fully
- [ ] Add config option: use_llm_rank_extraction
- [ ] Test accuracy vs pattern-based
- [ ] Document cost/accuracy tradeoffs

### Future Milestone: Historical Trends

- [ ] Add `llm-answer-watcher trends` command
- [ ] Query SQLite for appearance over time
- [ ] Generate trend charts
- [ ] Detect position changes

### Future Milestone: Cloud Backend

- [ ] Design HTTP API for runner
- [ ] Implement scheduling
- [ ] Add email/Slack alerts
- [ ] Multi-tenant workspaces
- [ ] DuckDB for columnar analytics

---

## Using This TODO

### For Solo Development

1. Work through milestones sequentially
2. Check off tasks as you complete them
3. Use git commits at natural breakpoints
4. Run tests frequently

### With Subagent Team

1. **For implementation tasks:** Ask Developer agent
   - "Implement config/loader.py per TODO.md section 1.2.2"

2. **For testing tasks:** Ask Tester agent
   - "Write tests for config/loader.py per TODO.md section 1.7"

3. **For review:** Ask Reviewer agent
   - "Review config module per TODO.md checklist"

4. **Iterate based on feedback**
   - Developer fixes issues found by Reviewer
   - Tester adds tests for edge cases

### Tracking Progress

- [ ] Update this file as tasks complete
- [ ] Commit TODO.md with code changes
- [ ] Use conventional commits for each milestone
- [ ] Tag releases: v0.1.0, v0.2.0, v1.0.0

### Questions?

- Refer to [SPECS.md](./SPECS.md) for detailed requirements
- Refer to [AGENTS.md](./.claude/AGENTS.md) for subagent usage
- Open an issue for clarifications

---

**Let's build something amazing!** 🚀
