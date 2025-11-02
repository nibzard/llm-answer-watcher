"""
HTML report generation for LLM Answer Watcher.

This module reads parsed JSON files from a run directory and generates a beautiful,
self-contained HTML report with inline CSS, no external dependencies.

Key features:
- Jinja2 templating with autoescaping enabled (XSS prevention)
- Mobile-responsive design with professional blue/green styling
- Cost tracking and formatting
- Visual appearance indicators (green  / red )
- Ranked lists with confidence indicators
- Self-contained HTML (inline CSS, no external assets)

Security:
- CRITICAL: Jinja2 autoescaping enabled to prevent HTML injection
- All user-supplied data (brand names, prompts) is automatically escaped

Example:
    >>> from pathlib import Path
    >>> from config.schema import RuntimeConfig
    >>> run_dir = "./output/2025-11-02T08-00-00Z"
    >>> html = generate_report(run_dir, "2025-11-02T08-00-00Z", config, results)
    >>> write_report(run_dir, config, results)
"""

import json
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config.schema import RuntimeConfig
from ..storage.layout import get_parsed_answer_filename
from ..storage.writer import write_report_html
from .cost_formatter import format_cost_usd

logger = logging.getLogger(__name__)


def generate_report(
    run_dir: str,
    run_id: str,
    config: RuntimeConfig,
    results: list[dict],
) -> str:
    """
    Generate HTML report from run results.

    Reads all parsed JSON files from run directory, aggregates data for the
    template, and renders a self-contained HTML report with inline CSS.

    Args:
        run_dir: Path to run output directory (contains parsed JSON files)
        run_id: Run identifier (timestamp slug)
        config: Runtime configuration with intents and models
        results: List of result dicts from runner (intent_id, provider, etc.)

    Returns:
        HTML string (self-contained, ready to write to file)

    Raises:
        FileNotFoundError: If run directory doesn't exist
        ValueError: If template rendering fails
        json.JSONDecodeError: If parsed JSON files are invalid

    Example:
        >>> html = generate_report(
        ...     "./output/2025-11-02T08-00-00Z",
        ...     "2025-11-02T08-00-00Z",
        ...     config,
        ...     [
        ...         {
        ...             "intent_id": "email-warmup",
        ...             "provider": "openai",
        ...             "model_name": "gpt-4o-mini",
        ...             "status": "success",
        ...             "cost_usd": 0.001
        ...         }
        ...     ]
        ... )
        >>> "LLM Answer Watcher Report" in html
        True

    Note:
        - Jinja2 autoescaping is enabled for XSS prevention
        - All costs are formatted with format_cost_usd()
        - Missing parsed files are logged but don't crash report generation
        - Template path is relative to this module's location
    """
    run_dir_path = Path(run_dir)

    # Validate run directory exists
    if not run_dir_path.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    logger.info(f"Generating HTML report for run: {run_id}")

    # Setup Jinja2 environment with autoescaping enabled (CRITICAL for security)
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml", "j2"]),
    )

    # Load template
    try:
        template = env.get_template("report.html.j2")
    except Exception as e:
        logger.error(f"Failed to load template: {e}", exc_info=True)
        raise ValueError(f"Cannot load report template: {e}") from e

    # Aggregate data for template
    template_data = _build_template_data(run_dir_path, run_id, config, results)

    # Render template
    try:
        html = template.render(**template_data)
        logger.info("HTML report generated successfully")
        return html
    except Exception as e:
        logger.error(f"Failed to render template: {e}", exc_info=True)
        raise ValueError(f"Cannot render report template: {e}") from e


def write_report(
    run_dir: str,
    config: RuntimeConfig,
    results: list[dict],
) -> None:
    """
    Generate and write HTML report to run directory.

    Convenience function that calls generate_report() and writes the output
    to report.html using storage.writer.

    Args:
        run_dir: Path to run output directory
        config: Runtime configuration with intents and models
        results: List of result dicts from runner

    Raises:
        FileNotFoundError: If run directory doesn't exist
        ValueError: If report generation fails
        OSError: If report cannot be written to disk

    Example:
        >>> write_report("./output/2025-11-02T08-00-00Z", config, results)

    Note:
        - Extracts run_id from run_dir path (last component)
        - Calls generate_report() then storage.writer.write_report_html()
        - Any errors during generation or writing are propagated
    """
    # Extract run_id from run_dir path
    run_id = Path(run_dir).name

    # Generate HTML
    html = generate_report(run_dir, run_id, config, results)

    # Write to disk
    write_report_html(run_dir, html)
    logger.info(f"HTML report written to: {run_dir}/report.html")


def _build_template_data(
    run_dir: Path,
    run_id: str,
    config: RuntimeConfig,
    results: list[dict],
) -> dict:
    """
    Build template data dictionary from run results.

    Aggregates all data needed for the Jinja2 template: summary stats,
    per-intent results with parsed mentions and rankings, cost totals.

    Args:
        run_dir: Path to run output directory
        run_id: Run identifier
        config: Runtime configuration
        results: List of result dicts from runner

    Returns:
        Dictionary with template variables (run_id, intents, costs, etc.)

    Note:
        - Reads parsed JSON files for each successful result
        - Handles missing files gracefully (logs warning, continues)
        - Formats all costs with format_cost_usd()
        - Sorts mentions by position for consistent display
    """
    # Calculate summary statistics
    total_intents = len(config.intents)
    total_models = len(config.models)
    successful_results = [r for r in results if r.get("status") == "success"]
    success_count = len(successful_results)
    total_count = len(results)
    success_rate = int(success_count / total_count * 100) if total_count > 0 else 0

    # Calculate total cost
    total_cost = sum(r.get("cost_usd", 0.0) for r in results)
    total_cost_formatted = format_cost_usd(total_cost)

    # Get timestamp from first result (if available)
    timestamp_utc = results[0].get("timestamp_utc", run_id) if results else run_id

    # Build list of unique models used
    models_used = []
    seen_models = set()
    for model in config.models:
        model_key = f"{model.provider}/{model.model_name}"
        if model_key not in seen_models:
            models_used.append(
                {
                    "provider": model.provider,
                    "model_name": model.model_name,
                }
            )
            seen_models.add(model_key)

    # Group results by intent
    intents_data = []
    for intent in config.intents:
        intent_results = [r for r in results if r.get("intent_id") == intent.id]

        # Load parsed data for each model result
        model_results = []
        for result in intent_results:
            model_data = _load_model_result(
                run_dir,
                result,
                intent.id,
            )
            if model_data:
                model_results.append(model_data)

        intents_data.append(
            {
                "intent_id": intent.id,
                "prompt": intent.prompt,
                "results": model_results,
            }
        )

    return {
        "run_id": run_id,
        "timestamp_utc": timestamp_utc,
        "total_cost_formatted": total_cost_formatted,
        "total_intents": total_intents,
        "total_models": total_models,
        "success_rate": success_rate,
        "models_used": models_used,
        "intents": intents_data,
    }


def _load_model_result(
    run_dir: Path,
    result: dict,
    intent_id: str,
) -> dict | None:
    """
    Load parsed result data for a single model's answer.

    Reads the parsed JSON file and extracts mentions, rankings, and metadata
    for template rendering.

    Args:
        run_dir: Path to run output directory
        result: Result dict from runner (with provider, model_name, status, cost)
        intent_id: Intent identifier (for filename generation)

    Returns:
        Dictionary with model result data for template, or None if loading fails

    Note:
        - Returns None for failed results (status != success)
        - Logs warnings for missing/invalid JSON files but doesn't crash
        - Sorts mentions by position for consistent display
        - Formats cost with format_cost_usd()
    """
    # Skip failed results
    if result.get("status") != "success":
        logger.warning(
            f"Skipping failed result: {intent_id} / "
            f"{result.get('provider')}/{result.get('model_name')}"
        )
        return None

    provider = result.get("provider")
    model_name = result.get("model_name")

    # Build path to parsed JSON file
    parsed_filename = get_parsed_answer_filename(intent_id, provider, model_name)
    parsed_path = run_dir / parsed_filename

    # Load parsed JSON
    if not parsed_path.exists():
        logger.warning(
            f"Parsed file not found: {parsed_path}. Skipping in report generation."
        )
        return None

    try:
        with parsed_path.open(encoding="utf-8") as f:
            parsed_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(
            f"Invalid JSON in {parsed_path}: {e}. Skipping in report generation.",
            exc_info=True,
        )
        return None
    except OSError as e:
        logger.error(
            f"Failed to read {parsed_path}: {e}. Skipping in report generation.",
            exc_info=True,
        )
        return None

    # Extract data from parsed result
    appeared_mine = parsed_data.get("appeared_mine", False)
    my_mentions = parsed_data.get("my_mentions", [])
    competitor_mentions = parsed_data.get("competitor_mentions", [])
    ranked_list = parsed_data.get("ranked_list", [])
    rank_extraction_method = parsed_data.get("rank_extraction_method", "pattern")
    rank_confidence = parsed_data.get("rank_confidence", 0.0)

    # Sort mentions by position for consistent display
    my_mentions_sorted = sorted(my_mentions, key=lambda m: m.get("match_position", 0))
    competitor_mentions_sorted = sorted(
        competitor_mentions, key=lambda m: m.get("match_position", 0)
    )

    # Format cost
    cost_usd = result.get("cost_usd", 0.0)
    cost_formatted = format_cost_usd(cost_usd)

    return {
        "provider": provider,
        "model_name": model_name,
        "appeared_mine": appeared_mine,
        "my_mentions": my_mentions_sorted,
        "competitor_mentions": competitor_mentions_sorted,
        "ranked_list": ranked_list,
        "rank_extraction_method": rank_extraction_method,
        "rank_confidence": rank_confidence,
        "cost_formatted": cost_formatted,
    }
