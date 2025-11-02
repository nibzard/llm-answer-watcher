"""
SQLite database initialization and schema management for LLM Answer Watcher.

This module provides database setup with schema versioning and migration support.
All timestamps are stored in ISO 8601 format with 'Z' suffix (UTC).

The database tracks:
- runs: Each CLI execution with metadata and totals
- answers_raw: Full LLM responses with usage and cost data
- mentions: Exploded brand mentions for analytics

Schema versioning ensures safe upgrades as features evolve.

Example usage:
    >>> from storage.db import init_db_if_needed
    >>> init_db_if_needed("./output/watcher.db")
    # Creates database with version 1 schema if needed
    # Or applies migrations if schema is outdated

Security:
    - ALL queries use parameterized statements to prevent SQL injection
    - NO API keys are ever stored in the database
    - Connection context managers ensure proper cleanup
"""

import logging
import sqlite3
from pathlib import Path

from ..utils.time import utc_timestamp

logger = logging.getLogger(__name__)

# Current schema version - increment when migrations are added
CURRENT_SCHEMA_VERSION = 1


def init_db_if_needed(db_path: str) -> None:
    """
    Initialize SQLite database with schema versioning.

    Creates the database file if it doesn't exist, initializes the schema_version
    table, checks the current schema version, and applies any needed migrations.

    This function is idempotent - safe to call multiple times. If the database
    already exists at the current schema version, it's a no-op.

    Args:
        db_path: Filesystem path to SQLite database file.
                 Parent directory must exist or be creatable.

    Raises:
        sqlite3.Error: If database creation or migration fails
        OSError: If parent directory cannot be created
        PermissionError: If database file is not writable

    Example:
        >>> init_db_if_needed("./output/watcher.db")
        # First call: creates database with v1 schema
        # Subsequent calls: no-op if schema is current

        >>> init_db_if_needed("/tmp/test.db")
        # Creates parent directory if needed

    Note:
        Uses transactions to ensure atomic schema migrations.
        If migration fails, database is rolled back to previous state.
        Always call this before performing database operations.
    """
    # Ensure parent directory exists
    db_path_obj = Path(db_path)
    db_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Connect to database (creates file if doesn't exist)
    with sqlite3.connect(db_path) as conn:
        # Enable foreign key constraints (disabled by default in SQLite)
        conn.execute("PRAGMA foreign_keys = ON")

        # Initialize schema_version table if needed
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        conn.commit()

        # Check current schema version
        current_version = get_schema_version(conn)

        if current_version < CURRENT_SCHEMA_VERSION:
            logger.info(
                f"Database schema upgrade needed: "
                f"v{current_version} -> v{CURRENT_SCHEMA_VERSION}"
            )
            apply_migrations(conn, current_version, CURRENT_SCHEMA_VERSION)
            logger.info(f"Database schema upgraded to v{CURRENT_SCHEMA_VERSION}")
        elif current_version == CURRENT_SCHEMA_VERSION:
            logger.debug(f"Database schema is current (v{CURRENT_SCHEMA_VERSION})")
        else:
            # This should never happen unless someone manually edited schema_version
            raise ValueError(
                f"Database schema version {current_version} is newer than "
                f"expected {CURRENT_SCHEMA_VERSION}. Update your software or "
                f"use a different database file."
            )


def get_schema_version(conn: sqlite3.Connection) -> int:
    """
    Get current schema version from database.

    Queries the schema_version table to determine which version of the schema
    is currently applied. Returns 0 if no version has been recorded (fresh database).

    Args:
        conn: Active SQLite database connection

    Returns:
        int: Current schema version (0 if no migrations applied yet)

    Example:
        >>> with sqlite3.connect("watcher.db") as conn:
        ...     version = get_schema_version(conn)
        ...     print(f"Schema version: {version}")
        Schema version: 1

    Note:
        This function does NOT create the schema_version table.
        Call init_db_if_needed() first to ensure table exists.
    """
    cursor = conn.execute("SELECT MAX(version) FROM schema_version")
    result = cursor.fetchone()[0]

    # MAX() returns None if table is empty
    return result if result is not None else 0


def apply_migrations(
    conn: sqlite3.Connection, from_version: int, to_version: int
) -> None:
    """
    Apply schema migrations from one version to another.

    Upgrades the database schema by applying all migrations between from_version
    and to_version (inclusive). Each migration runs in a transaction and is
    committed atomically. The schema_version table is updated after successful
    migration.

    Args:
        conn: Active SQLite database connection
        from_version: Starting schema version (0 for fresh database)
        to_version: Target schema version (usually CURRENT_SCHEMA_VERSION)

    Raises:
        sqlite3.Error: If any migration SQL fails (transaction rolled back)
        ValueError: If from_version > to_version (downgrades not supported)

    Example:
        >>> with sqlite3.connect("watcher.db") as conn:
        ...     # Upgrade from v0 to v1
        ...     apply_migrations(conn, 0, 1)
        ...     # Database now has runs, answers_raw, mentions tables

    Note:
        Migrations are applied sequentially. If migration to version N fails,
        database remains at version N-1. Partial migrations are rolled back.

        Future versions add more migration logic:
        - v1 -> v2: Add new columns or indexes
        - v2 -> v3: Modify constraints or add tables
    """
    if from_version > to_version:
        raise ValueError(
            f"Cannot downgrade schema from v{from_version} to v{to_version}. "
            f"Downgrades are not supported. Use a database backup instead."
        )

    # Apply each migration in sequence
    for target_version in range(from_version + 1, to_version + 1):
        logger.info(f"Applying migration to schema version {target_version}")

        # Use transaction for atomic migration
        try:
            conn.execute("BEGIN")

            if target_version == 1:
                _migrate_to_v1(conn)
            # Future migrations go here:
            # elif target_version == 2:
            #     _migrate_to_v2(conn)
            else:
                raise ValueError(f"No migration defined for version {target_version}")

            # Record successful migration
            timestamp = utc_timestamp()
            conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (target_version, timestamp),
            )

            conn.commit()
            logger.info(
                f"Successfully migrated to schema version {target_version} "
                f"at {timestamp}"
            )

        except Exception as e:
            conn.rollback()
            logger.error(
                f"Migration to version {target_version} failed: {e}", exc_info=True
            )
            raise sqlite3.Error(
                f"Failed to migrate database to version {target_version}: {e}"
            ) from e


def _migrate_to_v1(conn: sqlite3.Connection) -> None:
    """
    Migrate database schema to version 1.

    Creates initial tables for the LLM Answer Watcher:
    - runs: Track each CLI execution with run_id, timestamp, totals
    - answers_raw: Store full LLM responses with usage metadata
    - mentions: Exploded brand mentions for analytics queries

    Also creates indexes for common query patterns:
    - Timestamp-based queries (time series analysis)
    - Intent-based filtering
    - Brand name lookups
    - Rank position analysis

    Args:
        conn: Active SQLite database connection in transaction

    Raises:
        sqlite3.Error: If table creation or index creation fails

    Note:
        This migration is called automatically by apply_migrations().
        Do NOT call directly - use apply_migrations() instead.

        Schema design principles:
        - UNIQUE constraints prevent duplicate data
        - Foreign keys maintain referential integrity
        - Indexes optimize common query patterns
        - TEXT fields use ISO 8601 timestamps with 'Z' suffix
        - REAL fields store costs as USD with 6 decimal precision
    """
    # Create runs table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            timestamp_utc TEXT NOT NULL,
            total_intents INTEGER NOT NULL,
            total_models INTEGER NOT NULL,
            total_cost_usd REAL DEFAULT 0.0
        )
    """)

    # Create answers_raw table
    conn.execute("""
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
        )
    """)

    # Create mentions table
    conn.execute("""
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
        )
    """)

    # Create indexes for common queries
    # Timestamp indexes for time series analysis
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_mentions_timestamp
        ON mentions(timestamp_utc)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_answers_timestamp
        ON answers_raw(timestamp_utc)
    """)

    # Intent index for filtering by search query
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_mentions_intent
        ON mentions(intent_id)
    """)

    # Brand index for competitor analysis
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_mentions_brand
        ON mentions(normalized_name)
    """)

    # is_mine index for filtering own vs competitor mentions
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_mentions_mine
        ON mentions(is_mine)
    """)

    # Rank index for position-based queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_mentions_rank
        ON mentions(rank_position)
    """)

    logger.debug("Created schema v1 tables and indexes")


# ============================================================================
# Database Operations (CRUD)
# ============================================================================


def insert_run(
    conn: sqlite3.Connection,
    run_id: str,
    timestamp_utc: str,
    total_intents: int,
    total_models: int,
) -> None:
    """
    Insert a new run record into the runs table.

    Records the start of a CLI execution with metadata about the planned work
    (number of intents and models to query). The total_cost_usd field is
    initialized to 0.0 and updated later via update_run_cost().

    This function is idempotent - if a run with the same run_id already exists,
    the insert is skipped (due to PRIMARY KEY constraint).

    Args:
        conn: Active SQLite database connection
        run_id: Unique run identifier (usually timestamp-based)
        timestamp_utc: ISO 8601 timestamp with 'Z' suffix (e.g., "2025-11-02T08:00:00Z")
        total_intents: Number of buyer-intent queries in this run
        total_models: Number of LLM models being queried per intent

    Raises:
        sqlite3.Error: If database operation fails

    Example:
        >>> with sqlite3.connect("watcher.db") as conn:
        ...     insert_run(
        ...         conn,
        ...         run_id="2025-11-02T08-00-00Z",
        ...         timestamp_utc="2025-11-02T08:00:00Z",
        ...         total_intents=3,
        ...         total_models=2
        ...     )
        ...     conn.commit()

    Security:
        Uses parameterized query to prevent SQL injection.

    Note:
        Always call conn.commit() after insert to persist changes.
        Uses INSERT OR IGNORE to make operation idempotent.
    """
    conn.execute(
        """
        INSERT OR IGNORE INTO runs (
            run_id,
            timestamp_utc,
            total_intents,
            total_models,
            total_cost_usd
        ) VALUES (?, ?, ?, ?, 0.0)
        """,
        (run_id, timestamp_utc, total_intents, total_models),
    )
    logger.debug(
        f"Inserted run {run_id} with {total_intents} intents, {total_models} models"
    )


def insert_answer_raw(
    conn: sqlite3.Connection,
    run_id: str,
    intent_id: str,
    model_provider: str,
    model_name: str,
    timestamp_utc: str,
    prompt: str,
    answer_text: str,
    usage_meta_json: str | None = None,
    estimated_cost_usd: float | None = None,
) -> None:
    """
    Insert a raw LLM answer into the answers_raw table.

    Stores the complete LLM response with metadata for historical tracking.
    The answer_length is computed automatically from answer_text.

    This function is idempotent - if an answer for the same (run_id, intent_id,
    model_provider, model_name) already exists, the insert is skipped (due to
    UNIQUE constraint).

    Args:
        conn: Active SQLite database connection
        run_id: Run identifier (foreign key to runs.run_id)
        intent_id: Intent query identifier from config
        model_provider: LLM provider (e.g., "openai", "anthropic")
        model_name: Model identifier (e.g., "gpt-4o-mini")
        timestamp_utc: ISO 8601 timestamp when answer was generated
        prompt: Full prompt sent to LLM
        answer_text: Raw LLM response text
        usage_meta_json: Optional JSON-encoded usage metadata (tokens, etc.)
        estimated_cost_usd: Optional estimated cost in USD

    Raises:
        sqlite3.Error: If database operation fails

    Example:
        >>> import json
        >>> usage = {"prompt_tokens": 100, "completion_tokens": 500}
        >>> insert_answer_raw(
        ...     conn,
        ...     run_id="2025-11-02T08-00-00Z",
        ...     intent_id="email-warmup",
        ...     model_provider="openai",
        ...     model_name="gpt-4o-mini",
        ...     timestamp_utc="2025-11-02T08:00:05Z",
        ...     prompt="What are the best email warmup tools?",
        ...     answer_text="Here are top email warmup tools: ...",
        ...     usage_meta_json=json.dumps(usage),
        ...     estimated_cost_usd=0.0012
        ... )
        >>> conn.commit()

    Security:
        Uses parameterized query to prevent SQL injection.
        Does NOT log answer_text (may contain sensitive info).

    Note:
        Always call conn.commit() after insert to persist changes.
        Uses INSERT OR IGNORE to make operation idempotent.
    """
    answer_length = len(answer_text)

    conn.execute(
        """
        INSERT OR IGNORE INTO answers_raw (
            run_id,
            intent_id,
            model_provider,
            model_name,
            timestamp_utc,
            prompt,
            answer_text,
            answer_length,
            usage_meta_json,
            estimated_cost_usd
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            intent_id,
            model_provider,
            model_name,
            timestamp_utc,
            prompt,
            answer_text,
            answer_length,
            usage_meta_json,
            estimated_cost_usd,
        ),
    )
    logger.debug(
        f"Inserted answer for intent={intent_id}, model={model_provider}/{model_name}, "
        f"length={answer_length} chars"
    )


def insert_mention(
    conn: sqlite3.Connection,
    run_id: str,
    timestamp_utc: str,
    intent_id: str,
    model_provider: str,
    model_name: str,
    brand_name: str,
    normalized_name: str,
    is_mine: bool,
    first_position: int | None = None,
    rank_position: int | None = None,
    match_type: str = "exact",
) -> None:
    """
    Insert a brand mention into the mentions table.

    Records a single brand mention found in an LLM answer. This is the "exploded"
    view of answers - each brand gets its own row for analytics queries.

    This function is idempotent - if a mention for the same (run_id, intent_id,
    model_provider, model_name, normalized_name) already exists, the insert is
    skipped (due to UNIQUE constraint).

    Args:
        conn: Active SQLite database connection
        run_id: Run identifier (foreign key to runs.run_id)
        timestamp_utc: ISO 8601 timestamp when mention was extracted
        intent_id: Intent query identifier from config
        model_provider: LLM provider (e.g., "openai", "anthropic")
        model_name: Model identifier (e.g., "gpt-4o-mini")
        brand_name: Original brand name/alias as found in text
        normalized_name: Normalized brand name for grouping (lowercase)
        is_mine: True if this is our brand, False if competitor
        first_position: Character position of first occurrence in text (0-indexed)
        rank_position: Rank/position in ordered list (1-indexed, None if not ranked)
        match_type: Type of match ("exact", "fuzzy", "llm_assisted")

    Raises:
        sqlite3.Error: If database operation fails

    Example:
        >>> insert_mention(
        ...     conn,
        ...     run_id="2025-11-02T08-00-00Z",
        ...     timestamp_utc="2025-11-02T08:00:05Z",
        ...     intent_id="email-warmup",
        ...     model_provider="openai",
        ...     model_name="gpt-4o-mini",
        ...     brand_name="HubSpot",
        ...     normalized_name="hubspot",
        ...     is_mine=False,
        ...     first_position=42,
        ...     rank_position=1,
        ...     match_type="exact"
        ... )
        >>> conn.commit()

    Security:
        Uses parameterized query to prevent SQL injection.

    Note:
        Always call conn.commit() after insert to persist changes.
        Uses INSERT OR IGNORE to make operation idempotent.
        is_mine is stored as INTEGER (0/1) per SQLite convention.
    """
    is_mine_int = 1 if is_mine else 0

    conn.execute(
        """
        INSERT OR IGNORE INTO mentions (
            run_id,
            timestamp_utc,
            intent_id,
            model_provider,
            model_name,
            brand_name,
            normalized_name,
            is_mine,
            first_position,
            rank_position,
            match_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            timestamp_utc,
            intent_id,
            model_provider,
            model_name,
            brand_name,
            normalized_name,
            is_mine_int,
            first_position,
            rank_position,
            match_type,
        ),
    )
    logger.debug(
        f"Inserted mention: {normalized_name} (is_mine={is_mine}, rank={rank_position})"
    )


def update_run_cost(
    conn: sqlite3.Connection, run_id: str, total_cost_usd: float
) -> None:
    """
    Update the total cost for a run in the runs table.

    Updates the total_cost_usd field after all LLM queries have completed
    and individual costs have been calculated. This is typically called at
    the end of a CLI execution.

    Args:
        conn: Active SQLite database connection
        run_id: Run identifier to update
        total_cost_usd: Total estimated cost in USD across all queries

    Raises:
        sqlite3.Error: If database operation fails
        ValueError: If run_id does not exist (rowcount == 0)

    Example:
        >>> update_run_cost(conn, "2025-11-02T08-00-00Z", 0.0234)
        >>> conn.commit()

    Security:
        Uses parameterized query to prevent SQL injection.

    Note:
        Always call conn.commit() after update to persist changes.
        Raises ValueError if run_id doesn't exist (catches logic errors early).
    """
    cursor = conn.execute(
        "UPDATE runs SET total_cost_usd = ? WHERE run_id = ?",
        (total_cost_usd, run_id),
    )

    if cursor.rowcount == 0:
        raise ValueError(
            f"Cannot update cost for run_id={run_id}: run does not exist. "
            f"Call insert_run() first."
        )

    logger.debug(f"Updated run {run_id} total cost: ${total_cost_usd:.6f}")


def get_run_summary(conn: sqlite3.Connection, run_id: str) -> dict | None:
    """
    Retrieve summary information for a specific run.

    Fetches the run record with all metadata. Useful for reporting and
    debugging.

    Args:
        conn: Active SQLite database connection
        run_id: Run identifier to retrieve

    Returns:
        dict with keys: run_id, timestamp_utc, total_intents, total_models, total_cost_usd
        None if run_id does not exist

    Example:
        >>> summary = get_run_summary(conn, "2025-11-02T08-00-00Z")
        >>> print(summary)
        {
            "run_id": "2025-11-02T08-00-00Z",
            "timestamp_utc": "2025-11-02T08:00:00Z",
            "total_intents": 3,
            "total_models": 2,
            "total_cost_usd": 0.0234
        }

    Security:
        Uses parameterized query to prevent SQL injection.

    Note:
        Returns None if run doesn't exist (not an error condition).
    """
    cursor = conn.execute(
        """
        SELECT run_id, timestamp_utc, total_intents, total_models, total_cost_usd
        FROM runs
        WHERE run_id = ?
        """,
        (run_id,),
    )

    row = cursor.fetchone()
    if row is None:
        return None

    return {
        "run_id": row[0],
        "timestamp_utc": row[1],
        "total_intents": row[2],
        "total_models": row[3],
        "total_cost_usd": row[4],
    }
