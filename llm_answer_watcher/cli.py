"""
CLI entrypoint for LLM Answer Watcher.

Provides a dual-mode command-line interface with:
- Human-friendly output: Rich spinners, tables, progress bars, colored text
- Agent-friendly output: Structured JSON for AI automation
- Quiet mode: Tab-separated minimal output for shell scripts

Commands:
    run: Execute LLM queries and generate reports
    validate: Validate configuration without running queries

Exit codes:
    0: Success - all queries successful
    1: Configuration error (invalid YAML, missing API keys)
    2: Database error (cannot create/access SQLite)
    3: Partial failure (some queries failed, but run completed)
    4: Complete failure (no queries succeeded)

Examples:
    # Human-friendly output with progress bars
    llm-answer-watcher run --config watcher.config.yaml

    # Agent-friendly JSON output (no spinners, no colors)
    llm-answer-watcher run --config watcher.config.yaml --format json

    # Quiet mode for scripts (tab-separated)
    llm-answer-watcher run --config watcher.config.yaml --quiet

    # Automation with no prompts
    llm-answer-watcher run --config watcher.config.yaml --yes --format json

Security:
    - API keys are loaded from environment variables only
    - Errors may contain file paths but never API keys
    - All exceptions are caught and formatted appropriately
"""

import json
from pathlib import Path

import typer
from rich.traceback import install as install_rich_traceback

from llm_answer_watcher.config.loader import load_config
from llm_answer_watcher.llm_runner.runner import run_all
from llm_answer_watcher.report.generator import write_report
from llm_answer_watcher.storage.db import init_db_if_needed
from llm_answer_watcher.storage.layout import get_parsed_answer_filename
from llm_answer_watcher.utils.console import (
    create_progress_bar,
    error,
    info,
    output_mode,
    print_banner,
    print_final_summary,
    print_summary_table,
    spinner,
    success,
    warning,
)
from llm_answer_watcher.utils.logging import setup_logging

# Install Rich tracebacks for better error messages
install_rich_traceback(show_locals=False)


def _check_brands_appeared(
    output_dir: str, intent_id: str, provider: str, model_name: str
) -> bool:
    """
    Check if our brands appeared in the LLM response by reading parsed file.

    Reads the parsed JSON file for this intent/model combination and checks
    if the my_brands_mentioned list is non-empty.

    Args:
        output_dir: Directory containing run output files
        intent_id: Intent identifier (e.g., "email-warmup")
        provider: LLM provider name (e.g., "openai")
        model_name: Model name (e.g., "gpt-4o-mini")

    Returns:
        True if our brands were mentioned, False otherwise
    """
    parsed_filename = get_parsed_answer_filename(intent_id, provider, model_name)
    parsed_path = Path(output_dir) / parsed_filename

    if not parsed_path.exists():
        # Parsed file doesn't exist, assume no mentions
        return False

    try:
        with open(parsed_path, encoding='utf-8') as f:
            parsed_data = json.load(f)

        # Check if my_brands_mentioned list is non-empty
        my_brands = parsed_data.get("my_brands_mentioned", [])
        return bool(my_brands)

    except (json.JSONDecodeError, OSError, KeyError):
        # If we can't read the file or it's malformed, assume no mentions
        return False

# Exit codes
EXIT_SUCCESS = 0  # All queries successful
EXIT_CONFIG_ERROR = 1  # Config validation failed
EXIT_DB_ERROR = 2  # Database initialization failed
EXIT_PARTIAL_FAILURE = 3  # Some queries failed
EXIT_COMPLETE_FAILURE = 4  # All queries failed

# Create Typer app
app = typer.Typer(
    name="llm-answer-watcher",
    help="Monitor how LLMs talk about your brand vs competitors",
    add_completion=False,  # Skip shell completion for simplicity
)


@app.command()
def run(
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to YAML configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: 'text' (human-friendly) or 'json' (machine-readable)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output (tab-separated values)",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip all confirmation prompts (for automation)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable debug logging",
    ),
):
    """
    Execute LLM queries and generate brand mention report.

    This command will:
    1. Load your configuration (intents, brands, models)
    2. Query each LLM with each intent
    3. Extract brand mentions and rankings
    4. Save results to SQLite database
    5. Generate JSON artifacts
    6. Generate HTML report

    Output modes:
    - Default (text): Beautiful tables, progress bars, colors
    - JSON: Structured output for AI agents and automation
    - Quiet: Tab-separated for shell scripts

    Exit codes:
      0: All queries succeeded
      1: Configuration error
      2: Database error
      3: Partial failure (some queries failed)
      4: Complete failure (all queries failed)

    Examples:
      # Human mode (default)
      llm-answer-watcher run --config watcher.config.yaml

      # Agent mode for automation
      llm-answer-watcher run --config watcher.config.yaml --format json --yes

      # Quiet mode for scripts
      llm-answer-watcher run --config watcher.config.yaml --quiet
    """
    # Set global output mode based on flags
    output_mode.format = format
    output_mode.quiet = quiet

    # Setup logging level
    setup_logging(verbose=verbose)

    # Print banner (human mode only)
    version = _read_version()
    print_banner(version)

    # Load configuration
    try:
        with spinner("Loading configuration..."):
            runtime_config = load_config(config)

        success(
            f"Loaded {len(runtime_config.intents)} intents, "
            f"{len(runtime_config.models)} models"
        )

    except FileNotFoundError as e:
        error(f"Configuration file not found: {e}")
        raise typer.Exit(EXIT_CONFIG_ERROR)
    except ValueError as e:
        error(f"Configuration validation failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(EXIT_CONFIG_ERROR)
    except Exception as e:
        error(f"Unexpected error loading configuration: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(EXIT_CONFIG_ERROR)

    # Initialize database
    try:
        with spinner("Initializing database..."):
            init_db_if_needed(runtime_config.run_settings.sqlite_db_path)

        success(f"Database ready: {runtime_config.run_settings.sqlite_db_path}")

    except Exception as e:
        error(f"Failed to initialize database: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(EXIT_DB_ERROR)

    # Calculate total work
    total_queries = len(runtime_config.intents) * len(runtime_config.models)
    info(f"Will execute {total_queries} queries")

    # Estimate cost and confirm if expensive (human mode only, unless --yes)
    if output_mode.is_human() and not yes:
        # Rough estimate: average $0.002 per query
        estimated_cost = total_queries * 0.002

        if total_queries > 10 or estimated_cost > 0.10:
            warning(
                f"This will execute {total_queries} queries "
                f"(estimated cost: ${estimated_cost:.4f})"
            )
            if not typer.confirm("Continue?"):
                info("Cancelled by user")
                raise typer.Exit(EXIT_SUCCESS)

    # Execute queries with progress tracking
    try:
        # Create progress bar (no-op in agent/quiet modes)
        progress = create_progress_bar()

        with progress:
            # Add task in human mode
            if output_mode.is_human():
                task = progress.add_task(
                    f"Querying LLMs ({total_queries} total)", total=total_queries
                )

                # Define progress callback
                def progress_callback():
                    progress.advance(task)

            else:
                # No progress updates in agent/quiet modes
                progress_callback = None

            # Run all queries
            with (
                spinner("Running queries...")
                if not output_mode.is_human()
                else _nullcontext()
            ):
                results = run_all(runtime_config)

        # Generate HTML report
        with spinner("Generating report..."):
            # Build list of result dicts for report generator
            result_list = []
            for intent in runtime_config.intents:
                for model in runtime_config.models:
                    # Find matching result (success or error)
                    found_error = False
                    for error_record in results.get("errors", []):
                        if (
                            error_record["intent_id"] == intent.id
                            and error_record["model_provider"] == model.provider
                            and error_record["model_name"] == model.model_name
                        ):
                            result_list.append(
                                {
                                    "intent_id": intent.id,
                                    "provider": model.provider,
                                    "model_name": model.model_name,
                                    "status": "error",
                                    "cost_usd": 0.0,
                                    "timestamp_utc": results["timestamp_utc"],
                                }
                            )
                            found_error = True
                            break

                    if not found_error:
                        # Must be success
                        result_list.append(
                            {
                                "intent_id": intent.id,
                                "provider": model.provider,
                                "model_name": model.model_name,
                                "status": "success",
                                "cost_usd": results["total_cost_usd"]
                                / results["success_count"]
                                if results["success_count"] > 0
                                else 0.0,
                                "timestamp_utc": results["timestamp_utc"],
                            }
                        )

            write_report(results["output_dir"], runtime_config, result_list)

        success("Report generated successfully")

    except Exception as e:
        error(f"Run failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(EXIT_DB_ERROR)

    # Build summary table data
    summary_results = []
    for intent in runtime_config.intents:
        for model in runtime_config.models:
            # Check if this combination had an error
            found_error = False
            for error_record in results.get("errors", []):
                if (
                    error_record["intent_id"] == intent.id
                    and error_record["model_provider"] == model.provider
                    and error_record["model_name"] == model.model_name
                ):
                    summary_results.append(
                        {
                            "intent_id": intent.id,
                            "model": f"{model.provider}/{model.model_name}",
                            "appeared": False,
                            "cost": 0.0,
                            "status": "error",
                        }
                    )
                    found_error = True
                    break

            if not found_error:
                # Must be success - check if our brands actually appeared by reading parsed file
                appeared = _check_brands_appeared(
                    results["output_dir"], intent.id, model.provider, model.model_name
                )
                summary_results.append(
                    {
                        "intent_id": intent.id,
                        "model": f"{model.provider}/{model.model_name}",
                        "appeared": appeared,
                        "cost": results["total_cost_usd"] / results["success_count"]
                        if results["success_count"] > 0
                        else 0.0,
                        "status": "success",
                    }
                )

    # Print summary table
    print_summary_table(summary_results)

    # Print final summary
    print_final_summary(
        run_id=results["run_id"],
        output_dir=results["output_dir"],
        total_cost=results["total_cost_usd"],
        successful=results["success_count"],
        total=total_queries,
    )

    # Print report link (human mode only)
    if output_mode.is_human():
        report_path = Path(results["output_dir"]) / "report.html"
        info(f"View report: file://{report_path.absolute()}")

    # Determine exit code
    if results["success_count"] == 0:
        raise typer.Exit(EXIT_COMPLETE_FAILURE)
    if results["success_count"] < total_queries:
        raise typer.Exit(EXIT_PARTIAL_FAILURE)
    raise typer.Exit(EXIT_SUCCESS)


@app.command()
def validate(
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to YAML configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: 'text' or 'json'",
    ),
):
    """
    Validate configuration file without executing queries.

    Checks:
    - YAML syntax is valid
    - All required fields are present
    - Field values pass validation rules
    - API key environment variables are set

    Useful for:
    - CI/CD pipelines to check config syntax
    - Pre-flight checks before expensive runs
    - Testing API key resolution

    Exit codes:
      0: Configuration is valid
      1: Configuration is invalid

    Examples:
      # Validate config in human mode
      llm-answer-watcher validate --config watcher.config.yaml

      # Validate for CI/CD (JSON output)
      llm-answer-watcher validate --config watcher.config.yaml --format json
    """
    # Set global output mode
    output_mode.format = format

    with spinner("Validating configuration..."):
        try:
            runtime_config = load_config(config)

            success("Configuration is valid")
            info(f"Intents: {len(runtime_config.intents)}")
            info(f"Models: {len(runtime_config.models)}")
            info(f"Brands (mine): {len(runtime_config.brands.mine)}")
            info(f"Brands (competitors): {len(runtime_config.brands.competitors)}")

            if output_mode.is_agent():
                output_mode.add_json("valid", True)
                output_mode.add_json("intents_count", len(runtime_config.intents))
                output_mode.add_json("models_count", len(runtime_config.models))
                output_mode.add_json("my_brands_count", len(runtime_config.brands.mine))
                output_mode.add_json(
                    "competitor_brands_count", len(runtime_config.brands.competitors)
                )
                output_mode.flush_json()

            raise typer.Exit(EXIT_SUCCESS)

        except FileNotFoundError as e:
            error(f"Configuration file not found: {e}")

            if output_mode.is_agent():
                output_mode.add_json("valid", False)
                output_mode.add_json("error", str(e))
                output_mode.add_json("error_type", "file_not_found")
                output_mode.flush_json()

            raise typer.Exit(EXIT_CONFIG_ERROR)

        except ValueError as e:
            error(f"Validation failed: {e}")

            if output_mode.is_agent():
                output_mode.add_json("valid", False)
                output_mode.add_json("error", str(e))
                output_mode.add_json("error_type", "validation_error")
                output_mode.flush_json()

            raise typer.Exit(EXIT_CONFIG_ERROR)

        except typer.Exit:
            # Re-raise Typer exits (don't convert success to error)
            raise

        except Exception as e:
            error(f"Unexpected error: {e}")

            if output_mode.is_agent():
                output_mode.add_json("valid", False)
                output_mode.add_json("error", str(e))
                output_mode.add_json("error_type", "unknown_error")
                output_mode.flush_json()

            raise typer.Exit(EXIT_CONFIG_ERROR)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit",
    ),
):
    """
    LLM Answer Watcher - Monitor your brand mentions in LLM responses.

    Track how language models talk about your product compared to
    competitors across specific buyer-intent queries.

    Exit codes:
      0: Success
      1: Configuration error
      2: Database error
      3: Partial failure (some queries failed)
      4: Complete failure (all queries failed)

    Examples:
      # Run with default config
      llm-answer-watcher run --config watcher.config.yaml

      # Agent mode for automation
      llm-answer-watcher run --config watcher.config.yaml --format json --yes

      # Validate config before running
      llm-answer-watcher validate --config watcher.config.yaml

    Use 'llm-answer-watcher COMMAND --help' for detailed command documentation.
    """
    if version:
        from rich.console import Console

        console = Console()
        version_str = _read_version()
        console.print(
            f"[bold cyan]llm-answer-watcher[/bold cyan] version {version_str}"
        )
        console.print("Python CLI for monitoring brand mentions in LLM responses")
        raise typer.Exit(EXIT_SUCCESS)

    if ctx.invoked_subcommand is None:
        from rich.console import Console

        console = Console()
        console.print("[yellow]Use --help to see available commands[/yellow]")
        console.print()
        console.print("Quick start:")
        console.print("  llm-answer-watcher run --config watcher.config.yaml")
        console.print()
        console.print("Commands:")
        console.print("  run       Execute LLM queries and generate report")
        console.print("  validate  Validate configuration without running")


def _read_version() -> str:
    """
    Read version from VERSION file.

    Returns:
        Version string (e.g., "0.1.0")
    """
    try:
        version_file = Path(__file__).parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception:
        pass

    # Fallback version
    return "0.1.0"


class _nullcontext:
    """No-op context manager for conditional context usage."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


if __name__ == "__main__":
    app()
