"""
Core orchestration engine for LLM Answer Watcher.

This module implements the main "run_all" function that executes the complete
workflow: query LLMs, parse answers, write artifacts, store in database.

This is the internal "POST /run" contract - OSS CLI calls it in-process,
Cloud version will expose it over HTTP.

Key responsibilities:
- Generate run_id from current UTC timestamp
- Create output directory structure
- Loop through all (intent, model) combinations
- Call LLM clients with retry logic
- Parse answers using extractor module
- Write JSON artifacts (raw, parsed, error files)
- Insert data into SQLite database
- Generate run metadata summary
- Return structured result dict

Example:
    >>> from llm_answer_watcher.config.loader import load_config
    >>> config = load_config("examples/watcher.config.yaml")
    >>> result = run_all(config)
    >>> print(result["run_id"])
    '2025-11-02T08-00-00Z'
    >>> print(result["total_cost_usd"])
    0.0123

Architecture:
    This is the API-first contract. In OSS version, CLI calls this directly.
    In Cloud version, this becomes the HTTP endpoint handler.
"""

import json
import logging
import sqlite3
from dataclasses import asdict, dataclass

from ..config.schema import RuntimeConfig
from ..extractor.parser import parse_answer
from ..storage.db import insert_answer_raw, insert_mention, insert_run
from ..storage.writer import (
    create_run_directory,
    write_error,
    write_parsed_answer,
    write_raw_answer,
    write_run_meta,
)
from ..utils.time import run_id_from_timestamp, utc_timestamp
from .models import build_client

logger = logging.getLogger(__name__)


@dataclass
class RawAnswerRecord:
    """
    Intermediate data structure for raw LLM response.

    Holds the raw answer from an LLM along with metadata before writing
    to JSON and database. Used in run_all() orchestration.

    Attributes:
        intent_id: Intent query identifier (e.g., "email-warmup")
        prompt: The actual prompt text sent to LLM
        model_provider: LLM provider name (e.g., "openai", "anthropic")
        model_name: Model identifier (e.g., "gpt-4o-mini", "claude-3-5-sonnet")
        timestamp_utc: UTC timestamp when answer was generated (ISO 8601)
        answer_text: Raw text response from LLM
        answer_length: Character count of answer_text
        usage_meta: Token usage dict from LLM API (prompt_tokens, completion_tokens)
        estimated_cost_usd: Estimated API cost in USD based on token usage
        web_search_results: Optional list of web search results if tools were used
        web_search_count: Number of web searches performed (0 if no web search)

    Example:
        >>> record = RawAnswerRecord(
        ...     intent_id="email-warmup",
        ...     prompt="What are the best email warmup tools?",
        ...     model_provider="openai",
        ...     model_name="gpt-4o-mini",
        ...     timestamp_utc="2025-11-02T08:00:00Z",
        ...     answer_text="Here are the best tools...",
        ...     answer_length=500,
        ...     usage_meta={"prompt_tokens": 100, "completion_tokens": 400},
        ...     estimated_cost_usd=0.001,
        ...     web_search_results=None,
        ...     web_search_count=0
        ... )
    """

    intent_id: str
    prompt: str
    model_provider: str
    model_name: str
    timestamp_utc: str
    answer_text: str
    answer_length: int
    usage_meta: dict
    estimated_cost_usd: float
    web_search_results: list[dict] | None = None
    web_search_count: int = 0


def run_all(config: RuntimeConfig) -> dict:
    """
    Execute complete LLM query workflow and return results.

    This is the core orchestration function that runs all queries across
    all intents and models, parses results, writes artifacts, and stores
    data in SQLite.

    **This is the internal API contract** - designed to be called in-process
    by OSS CLI or exposed over HTTP in Cloud version.

    Args:
        config: Runtime configuration with intents, models, API keys, paths

    Returns:
        Summary dictionary with structure:
        {
            "run_id": "2025-11-02T08-00-00Z",
            "timestamp_utc": "2025-11-02T08:00:00Z",
            "output_dir": "./output/2025-11-02T08-00-00Z",
            "total_intents": 3,
            "total_models": 2,
            "total_queries": 6,
            "success_count": 5,
            "error_count": 1,
            "total_cost_usd": 0.0123,
            "errors": [
                {
                    "intent_id": "sales-tools",
                    "model_provider": "openai",
                    "model_name": "gpt-4o",
                    "error_message": "API rate limit exceeded"
                }
            ]
        }

    Raises:
        OSError: If output directory cannot be created
        PermissionError: If insufficient permissions for file/DB operations
        Exception: Database errors are logged but don't stop execution

    Example:
        >>> config = load_config("examples/watcher.config.yaml")
        >>> result = run_all(config)
        >>> success = result['success_count']
        >>> total = result['total_queries']
        >>> print(f"Completed {success}/{total} queries")
        Completed 5/6 queries
        >>> print(f"Total cost: ${result['total_cost_usd']:.4f}")
        Total cost: $0.0123

    Implementation notes:
        - Queries are executed sequentially (no async in v1)
        - Each query failure is logged but doesn't stop execution
        - Error files are written for failed queries
        - Database errors are logged but don't prevent JSON output
        - Cost is estimated, not exact (depends on provider pricing)
    """
    # Generate run identifier from current UTC timestamp
    run_id = run_id_from_timestamp()
    timestamp_utc = utc_timestamp()

    logger.info(f"Starting run {run_id}")
    logger.info(
        f"Config: {len(config.intents)} intents, {len(config.models)} models, "
        f"output_dir={config.run_settings.output_dir}"
    )

    # Create output directory for this run
    run_dir = create_run_directory(config.run_settings.output_dir, run_id)
    logger.info(f"Created run directory: {run_dir}")

    # Initialize tracking variables
    total_queries = len(config.intents) * len(config.models)
    success_count = 0
    error_count = 0
    total_cost_usd = 0.0
    errors = []

    # Insert run record into database
    try:
        with sqlite3.connect(config.run_settings.sqlite_db_path) as conn:
            insert_run(
                conn=conn,
                run_id=run_id,
                timestamp_utc=timestamp_utc,
                total_intents=len(config.intents),
                total_models=len(config.models),
            )
            conn.commit()
        logger.debug(f"Inserted run record: run_id={run_id}")
    except Exception as e:
        logger.error(f"Failed to insert run record into database: {e}", exc_info=True)
        # Continue execution - database is not critical

    # Execute queries for all (intent, model) combinations
    for intent in config.intents:
        for model_config in config.models:
            logger.info(
                f"Processing: intent={intent.id}, provider={model_config.provider}, "
                f"model={model_config.model_name}"
            )

            try:
                # Build LLM client for this model
                client = build_client(
                    provider=model_config.provider,
                    model_name=model_config.model_name,
                    api_key=model_config.api_key,
                    system_prompt=model_config.system_prompt,
                    tools=model_config.tools,
                    tool_choice=model_config.tool_choice,
                )

                # Generate answer with retry logic
                response = client.generate_answer(intent.prompt)

                # Extract response data
                answer_text = response.answer_text
                cost_usd = response.cost_usd

                # Create usage metadata for storage with actual token breakdown
                usage_meta = {
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_tokens": response.tokens_used,
                }

                # Create raw answer record
                raw_record = RawAnswerRecord(
                    intent_id=intent.id,
                    prompt=intent.prompt,
                    model_provider=model_config.provider,
                    model_name=model_config.model_name,
                    timestamp_utc=utc_timestamp(),
                    answer_text=answer_text,
                    answer_length=len(answer_text),
                    usage_meta=usage_meta,
                    estimated_cost_usd=cost_usd,
                    web_search_results=response.web_search_results,
                    web_search_count=response.web_search_count,
                )

                # Write raw answer JSON
                write_raw_answer(
                    run_dir=run_dir,
                    intent_id=intent.id,
                    provider=model_config.provider,
                    model=model_config.model_name,
                    data=asdict(raw_record),
                )

                # Insert raw answer into database
                try:
                    # Serialize web search results to JSON if present
                    web_search_json = None
                    if response.web_search_results:
                        web_search_json = json.dumps(response.web_search_results)

                    with sqlite3.connect(config.run_settings.sqlite_db_path) as conn:
                        insert_answer_raw(
                            conn=conn,
                            run_id=run_id,
                            intent_id=intent.id,
                            model_provider=model_config.provider,
                            model_name=model_config.model_name,
                            timestamp_utc=raw_record.timestamp_utc,
                            prompt=intent.prompt,
                            answer_text=answer_text,
                            usage_meta_json=json.dumps(usage_meta),
                            estimated_cost_usd=cost_usd,
                            web_search_count=response.web_search_count,
                            web_search_results_json=web_search_json,
                        )
                        conn.commit()
                except Exception as e:
                    logger.error(
                        f"Failed to insert answer into database: {e}", exc_info=True
                    )

                # Parse answer to extract mentions and rankings
                extraction_result = parse_answer(
                    answer_text=answer_text,
                    brands=config.brands,
                    intent_id=intent.id,
                    provider=model_config.provider,
                    model_name=model_config.model_name,
                    timestamp_utc=raw_record.timestamp_utc,
                )

                # Write parsed answer JSON
                parsed_data = {
                    "appeared_mine": extraction_result.appeared_mine,
                    "my_mentions": [
                        {
                            "original_text": m.original_text,
                            "normalized_name": m.normalized_name,
                            "brand_category": m.brand_category,
                            "match_position": m.match_position,
                        }
                        for m in extraction_result.my_mentions
                    ],
                    "competitor_mentions": [
                        {
                            "original_text": m.original_text,
                            "normalized_name": m.normalized_name,
                            "brand_category": m.brand_category,
                            "match_position": m.match_position,
                        }
                        for m in extraction_result.competitor_mentions
                    ],
                    "ranked_list": [
                        {
                            "brand_name": r.brand_name,
                            "rank_position": r.rank_position,
                            "confidence": r.confidence,
                        }
                        for r in extraction_result.ranked_list
                    ],
                    "rank_extraction_method": extraction_result.rank_extraction_method,
                    "rank_confidence": extraction_result.rank_confidence,
                }

                write_parsed_answer(
                    run_dir=run_dir,
                    intent_id=intent.id,
                    provider=model_config.provider,
                    model=model_config.model_name,
                    data=parsed_data,
                )

                # Insert mentions into database
                all_mentions = (
                    extraction_result.my_mentions
                    + extraction_result.competitor_mentions
                )
                for mention in all_mentions:
                    try:
                        # Determine if this is my brand
                        is_mine = mention.brand_category == "mine"

                        # Find rank position if this brand is in ranked list
                        rank_position = None
                        for ranked in extraction_result.ranked_list:
                            if ranked.brand_name == mention.normalized_name:
                                rank_position = ranked.rank_position
                                break

                        with sqlite3.connect(
                            config.run_settings.sqlite_db_path
                        ) as conn:
                            insert_mention(
                                conn=conn,
                                run_id=run_id,
                                timestamp_utc=raw_record.timestamp_utc,
                                intent_id=intent.id,
                                model_provider=model_config.provider,
                                model_name=model_config.model_name,
                                brand_name=mention.original_text,
                                normalized_name=mention.normalized_name,
                                is_mine=is_mine,
                                rank_position=rank_position,
                                match_type="exact",  # Default match type
                            )
                            conn.commit()
                    except Exception as e:
                        logger.error(
                            f"Failed to insert mention into database: {e}",
                            exc_info=True,
                        )

                # Update success tracking
                success_count += 1
                total_cost_usd += cost_usd

                logger.info(
                    f"Success: intent={intent.id}, provider={model_config.provider}, "
                    f"model={model_config.model_name}, cost=${cost_usd:.6f}, "
                    f"appeared_mine={extraction_result.appeared_mine}"
                )

            except Exception as e:
                # Query failed - write error file and track
                error_message = str(e)
                logger.error(
                    f"Failed query: intent={intent.id}, "
                    f"provider={model_config.provider}, "
                    f"model={model_config.model_name}, error={error_message}",
                    exc_info=True,
                )

                write_error(
                    run_dir=run_dir,
                    intent_id=intent.id,
                    provider=model_config.provider,
                    model=model_config.model_name,
                    error_message=error_message,
                )

                error_count += 1
                errors.append(
                    {
                        "intent_id": intent.id,
                        "model_provider": model_config.provider,
                        "model_name": model_config.model_name,
                        "error_message": error_message,
                    }
                )

    # Generate run metadata summary
    run_meta = {
        "run_id": run_id,
        "timestamp_utc": timestamp_utc,
        "output_dir": run_dir,
        "total_intents": len(config.intents),
        "total_models": len(config.models),
        "total_queries": total_queries,
        "success_count": success_count,
        "error_count": error_count,
        "total_cost_usd": round(total_cost_usd, 6),
        "my_brands": config.brands.mine,
        "competitors": config.brands.competitors,
        "database_path": config.run_settings.sqlite_db_path,
    }

    # Write run metadata JSON
    write_run_meta(run_dir=run_dir, meta=run_meta)

    logger.info(
        f"Run {run_id} complete: {success_count}/{total_queries} successful, "
        f"total_cost=${total_cost_usd:.6f}"
    )

    # Return summary dict (for API contract)
    return {
        "run_id": run_id,
        "timestamp_utc": timestamp_utc,
        "output_dir": run_dir,
        "total_intents": len(config.intents),
        "total_models": len(config.models),
        "total_queries": total_queries,
        "success_count": success_count,
        "error_count": error_count,
        "total_cost_usd": round(total_cost_usd, 6),
        "errors": errors,
    }
