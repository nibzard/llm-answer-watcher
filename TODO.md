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

- [ ] **Create module directory structure**
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

- [ ] **Create pyproject.toml**
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

- [ ] **Create VERSION file**
  - Initial version: `0.1.0`

- [ ] **Create SCHEMA_VERSION file**
  - Initial schema version: `1`

- [ ] **Verify LICENSE exists** (MIT, already created)

- [ ] **Create requirements.txt** (fallback for pip users)
  - Generate from pyproject.toml

### 1.2 Config Module (config/)

#### 1.2.1 config/schema.py

- [ ] **Define Pydantic models:**
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

- [ ] **Implement `load_config(config_path: str) -> RuntimeConfig`**
  - [ ] Load YAML file from path
  - [ ] Handle FileNotFoundError with clear message
  - [ ] Parse YAML into dict
  - [ ] Validate with WatcherConfig Pydantic model
  - [ ] Catch ValidationError and provide helpful error messages
  - [ ] For each ModelConfig, resolve environment variable
  - [ ] Check if env var exists with `os.environ.get()`
  - [ ] Raise ValueError if API key env var missing
  - [ ] Build list of RuntimeModel instances with resolved keys
  - [ ] Construct and return RuntimeConfig
  - [ ] Add comprehensive docstring with Args, Returns, Raises
  - [ ] **Security:** Never log API keys

### 1.3 Utils Module - Time (utils/time.py)

- [ ] **Implement UTC timestamp utilities:**
  - [ ] `utc_now() -> datetime`
    - Return current time in UTC with timezone info

  - [ ] `utc_timestamp() -> str`
    - Return ISO 8601 timestamp with 'Z' suffix
    - Format: `YYYY-MM-DDTHH:MM:SSZ`

  - [ ] `run_id_from_timestamp(dt: datetime | None = None) -> str`
    - Generate run_id slug from timestamp
    - Format: `YYYY-MM-DDTHH-MM-SSZ` (hyphens instead of colons)
    - Default to current time if dt is None

  - [ ] `parse_timestamp(ts: str) -> datetime`
    - Parse ISO 8601 timestamp to datetime
    - Raise ValueError if no 'Z' suffix
    - Raise ValueError if invalid format

### 1.4 Utils Module - Logging (utils/logging.py)

- [ ] **Setup structured JSON logging:**
  - [ ] Configure Python logging module
  - [ ] Set default level to INFO
  - [ ] Add --verbose flag support for DEBUG
  - [ ] Format logs as JSON with fields:
    - `timestamp`: ISO 8601 UTC
    - `level`: INFO, WARNING, ERROR, DEBUG
    - `component`: module name
    - `message`: human-readable description
    - `context`: dict with additional data
    - `run_id`: current run ID if available

  - [ ] Output to stderr (stdout reserved for user output)
  - [ ] **Implement redaction for secrets:**
    - Never log API keys
    - Only log last 4 chars if needed: `sk-...X7Z9`

  - [ ] Create helper functions:
    - [ ] `get_logger(component: str) -> Logger`
    - [ ] `log_with_context(level, message, context)`

### 1.5 Storage Module - Database (storage/db.py)

#### 1.5.1 Schema Definition

- [ ] **Implement `init_db_if_needed(db_path: str) -> None`**
  - [ ] Connect to SQLite database
  - [ ] Create `schema_version` table if not exists
  - [ ] Create `runs` table if not exists
  - [ ] Create `answers_raw` table if not exists
  - [ ] Create `mentions` table if not exists
  - [ ] Create indexes on common query columns
  - [ ] Check current schema version
  - [ ] Run migrations if needed (call storage.migrations)
  - [ ] Close connection properly

- [ ] **Schema: `schema_version` table**
  ```sql
  CREATE TABLE IF NOT EXISTS schema_version (
      version INTEGER PRIMARY KEY,
      applied_at TEXT NOT NULL
  );
  ```

- [ ] **Schema: `runs` table**
  ```sql
  CREATE TABLE IF NOT EXISTS runs (
      run_id TEXT PRIMARY KEY,
      timestamp_utc TEXT NOT NULL,
      total_intents INTEGER NOT NULL,
      total_models INTEGER NOT NULL,
      total_cost_usd REAL DEFAULT 0.0
  );
  ```

- [ ] **Schema: `answers_raw` table**
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

- [ ] **Schema: `mentions` table**
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

- [ ] **Create indexes:**
  ```sql
  CREATE INDEX IF NOT EXISTS idx_mentions_timestamp ON mentions(timestamp_utc);
  CREATE INDEX IF NOT EXISTS idx_mentions_intent ON mentions(intent_id);
  CREATE INDEX IF NOT EXISTS idx_mentions_brand ON mentions(normalized_name);
  CREATE INDEX IF NOT EXISTS idx_mentions_mine ON mentions(is_mine);
  CREATE INDEX IF NOT EXISTS idx_mentions_rank ON mentions(rank_position);
  CREATE INDEX IF NOT EXISTS idx_answers_timestamp ON answers_raw(timestamp_utc);
  ```

#### 1.5.2 Database Operations

- [ ] **Implement `insert_run(conn, run_id, timestamp_utc, total_intents, total_models)`**
  - [ ] Use parameterized query (prevent SQL injection)
  - [ ] Handle UNIQUE constraint (idempotent)
  - [ ] Commit transaction

- [ ] **Implement `insert_answer_raw(conn, ...)`**
  - [ ] Insert into answers_raw table
  - [ ] Use parameterized query
  - [ ] Handle UNIQUE constraint
  - [ ] Store usage_meta as JSON string

- [ ] **Implement `insert_mention(conn, ...)`**
  - [ ] Insert into mentions table
  - [ ] Use parameterized query
  - [ ] Handle UNIQUE constraint
  - [ ] Store is_mine as 1 or 0

- [ ] **Implement `update_run_cost(conn, run_id, total_cost)`**
  - [ ] Update runs table with final cost
  - [ ] Use parameterized query

### 1.6 Storage Module - Migrations (storage/migrations.py)

- [ ] **Create migration framework:**
  - [ ] `CURRENT_SCHEMA_VERSION = 1` constant

  - [ ] `get_current_version(conn) -> int`
    - Query schema_version table
    - Return max version or 0 if empty

  - [ ] `apply_migrations(conn, from_version: int)`
    - Apply all migrations from from_version to CURRENT
    - Call migration functions in order
    - Insert version record after each migration
    - Commit transactions

  - [ ] `migration_1(conn)`
    - Initial schema (already created by init_db)
    - Record version 1 application

### 1.7 Testing - Milestone 1

- [ ] **Test config/loader.py:**
  - [ ] Test loading valid config file
  - [ ] Test FileNotFoundError for missing file
  - [ ] Test ValidationError for invalid YAML structure
  - [ ] Test ValidationError for duplicate intent IDs
  - [ ] Test ValidationError for empty brand aliases
  - [ ] Test ValueError for missing env var
  - [ ] Test ValueError for empty API key in env
  - [ ] Test all Pydantic validators fire correctly
  - [ ] Use pytest fixtures for temp config files
  - [ ] Mock os.environ for API key resolution

- [ ] **Test utils/time.py:**
  - [ ] Test utc_now() returns UTC datetime
  - [ ] Test utc_timestamp() format is correct
  - [ ] Test run_id_from_timestamp() format
  - [ ] Test parse_timestamp() with valid input
  - [ ] Test parse_timestamp() raises on missing 'Z'
  - [ ] Test parse_timestamp() raises on invalid format
  - [ ] Use freezegun to mock time

- [ ] **Test storage/db.py:**
  - [ ] Test init_db_if_needed() creates tables
  - [ ] Test schema_version table created
  - [ ] Test insert_run() with new run_id
  - [ ] Test insert_run() idempotent (duplicate run_id)
  - [ ] Test insert_answer_raw() with all fields
  - [ ] Test UNIQUE constraint on answers_raw
  - [ ] Test insert_mention() with all fields
  - [ ] Test UNIQUE constraint on mentions
  - [ ] Test update_run_cost() updates correctly
  - [ ] Test indexes exist
  - [ ] Use temp database for tests (tmp_path fixture)

- [ ] **Test storage/migrations.py:**
  - [ ] Test get_current_version() on empty DB
  - [ ] Test get_current_version() on initialized DB
  - [ ] Test apply_migrations() from version 0 to 1
  - [ ] Test schema_version table populated after migration

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

- [ ] **Define `LLMClient` Protocol:**
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

- [ ] **Implement `build_client(provider: str, model_name: str, api_key: str) -> LLMClient`**
  - [ ] Check provider in supported list
  - [ ] If provider == "openai", return OpenAIClient instance
  - [ ] If provider == "anthropic", raise NotImplementedError (stub for future)
  - [ ] Raise ValueError for unsupported provider
  - [ ] Add comprehensive docstring

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

- [ ] **Implement `OpenAIClient` class:**
  - [ ] `__init__(self, model_name: str, api_key: str)`
    - Store model_name and api_key
    - Create httpx.Client with timeout=30.0

  - [ ] `@retry(...)` decorator with tenacity config

  - [ ] `generate_answer(self, prompt: str) -> tuple[str, dict]`
    - [ ] Build chat completion request:
      - System message: "You are an unbiased market analyst. Provide factual, balanced recommendations."
      - User message: prompt
    - [ ] Make POST request to OpenAI chat completions endpoint
    - [ ] Set Authorization header with Bearer token
    - [ ] Handle non-retry status codes (401, 400, 404)
      - Raise immediately without retry
    - [ ] Handle retry status codes (429, 500+)
      - Let tenacity handle retry
    - [ ] Extract answer text from response
    - [ ] Extract usage metadata (prompt_tokens, completion_tokens, etc.)
    - [ ] Log success with context (no API key in logs)
    - [ ] On final failure, raise RuntimeError with descriptive message
    - [ ] Include request_id in error if available
    - [ ] Return (answer_text, usage_meta)

  - [ ] `close(self)`
    - Close httpx client

- [ ] **Add comprehensive docstrings to all methods**

### 2.4 Utils Module - Cost Estimation (utils/cost.py)

- [ ] **Define pricing table:**
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

- [ ] **Implement `estimate_cost(provider: str, model: str, usage_meta: dict) -> float`**
  - [ ] Get pricing for provider/model from PRICING table
  - [ ] Return 0.0 with warning if pricing unavailable
  - [ ] Extract prompt_tokens and completion_tokens from usage_meta
  - [ ] Calculate: (input_tokens * input_price) + (output_tokens * output_price)
  - [ ] Round to 6 decimal places
  - [ ] Return cost in USD
  - [ ] Add comprehensive docstring with disclaimer

- [ ] **Add pricing update reminder in comments:**
  - Note that pricing should be updated periodically
  - Link to provider pricing pages

### 2.5 Extractor Module - Mention Detector (extractor/mention_detector.py)

- [ ] **Define `Mention` dataclass:**
  - Fields: `brand_name: str`, `normalized_name: str`, `first_position: int`, `match_type: str`

- [ ] **Implement helper functions:**
  - [ ] `normalize_brand_name(name: str) -> str`
    - Lowercase
    - Strip punctuation
    - Collapse whitespace
    - Return normalized form

  - [ ] `create_word_boundary_pattern(alias: str) -> re.Pattern`
    - Escape special regex characters with `re.escape()`
    - Wrap with word boundaries: `\b{escaped}\b`
    - Compile with `re.IGNORECASE`
    - Return pattern

- [ ] **Implement `detect_exact_mentions(text: str, brand_aliases: list[str]) -> list[Mention]`**
  - [ ] For each brand alias:
    - Create word-boundary regex pattern
    - Search for matches in text
    - Record first occurrence position
    - Store original brand name and normalized name
    - Mark match_type as "exact"
  - [ ] Deduplicate by normalized name (keep earliest)
  - [ ] Return list of Mention objects

- [ ] **Implement `detect_fuzzy_mentions(text: str, brand_aliases: list[str], threshold: float = 0.9) -> list[Mention]`**
  - [ ] Import rapidfuzz.fuzz
  - [ ] For each brand alias not found by exact match:
    - Use rapidfuzz to find similar strings in text
    - Check similarity score >= threshold
    - Record match position
    - Mark match_type as "fuzzy"
  - [ ] Return list of Mention objects

- [ ] **Implement `detect_mentions(text: str, my_brands: list[str], competitor_brands: list[str], fuzzy: bool = False) -> tuple[list[Mention], list[Mention]]`**
  - [ ] Detect exact mentions for my_brands
  - [ ] Detect exact mentions for competitor_brands
  - [ ] If fuzzy=True:
    - Detect fuzzy mentions for brands not found exactly
  - [ ] Sort mentions by first_position
  - [ ] Return (my_mentions, competitor_mentions)

### 2.6 Extractor Module - Rank Extractor (extractor/rank_extractor.py)

- [ ] **Define `RankedBrand` dataclass:**
  - Fields: `brand_name: str`, `rank_position: int`, `confidence: float`

- [ ] **Implement pattern-based extraction:**
  - [ ] `extract_ranked_list_pattern(text: str, known_brands: list[str]) -> tuple[list[RankedBrand], float]`
    - [ ] Look for numbered lists: `1. ToolName`, `2. ToolName`
    - [ ] Look for bullet lists: `- ToolName`, `• ToolName`
    - [ ] Look for markdown headers: `## ToolName`
    - [ ] Extract tool names after markers
    - [ ] Match against known_brands with fuzzy matching
    - [ ] Assign rank_position based on order (0 = top)
    - [ ] Calculate confidence:
      - 1.0: clear numbered list
      - 0.8: bullet list with consistent structure
      - 0.5: inferred from mention order
      - 0.3: no clear structure
    - [ ] Deduplicate in first-seen order
    - [ ] Return (ranked_list, confidence)

- [ ] **Implement LLM-assisted extraction (stub for v1):**
  - [ ] `extract_ranked_list_llm(text: str, known_brands: list[str], client: LLMClient) -> tuple[list[RankedBrand], float]`
    - [ ] Build extraction prompt
    - [ ] Call LLM with structured extraction request
    - [ ] Parse JSON response
    - [ ] Match against known_brands
    - [ ] Return (ranked_list, 0.95) for high confidence
    - [ ] Fallback to pattern-based if LLM call fails
    - [ ] Note: This is optional and disabled by default in v1

### 2.7 Extractor Module - Parser (extractor/parser.py)

- [ ] **Define `ExtractionResult` dataclass:**
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

- [ ] **Implement `parse_answer(answer_text: str, brands: Brands, intent_id: str, provider: str, model_name: str, timestamp_utc: str, use_llm_extraction: bool = False) -> ExtractionResult`**
  - [ ] Call detect_mentions() to get my_mentions and competitor_mentions
  - [ ] Set appeared_mine = len(my_mentions) > 0
  - [ ] Combine my_brands + competitor_brands for ranking
  - [ ] Call extract_ranked_list_pattern() to get ranked list
  - [ ] If use_llm_extraction=True (future):
    - Call extract_ranked_list_llm() instead
  - [ ] Build ExtractionResult with all fields
  - [ ] Return result

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
