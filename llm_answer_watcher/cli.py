"""
CLI entrypoint for LLM Answer Watcher.

Provides a dual-mode command-line interface with:
- Human-friendly output: Rich spinners, tables, progress bars, colored text
- Agent-friendly output: Structured JSON for AI automation
- Quiet mode: Tab-separated minimal output for shell scripts

Commands:
    run: Execute LLM queries and generate reports
    validate: Validate configuration without running queries
    eval: Run evaluation suite to test extraction accuracy
    prices: Manage LLM pricing data (show, refresh, list)

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
from contextlib import nullcontext
from pathlib import Path

import typer
from rich.traceback import install as install_rich_traceback

from llm_answer_watcher.config.loader import load_config
from llm_answer_watcher.evals.runner import run_eval_suite
from llm_answer_watcher.llm_runner.runner import run_all
from llm_answer_watcher.report.generator import write_report
from llm_answer_watcher.storage.db import init_db_if_needed
from llm_answer_watcher.storage.eval_db import (
    init_eval_db_if_needed,
    store_eval_results,
)
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
    if the my_mentions list is non-empty. This function is defensive and
    returns False on any error condition.

    Args:
        output_dir: Directory containing run output files
        intent_id: Intent identifier (e.g., "email-warmup")
        provider: LLM provider name (e.g., "openai")
        model_name: Model name (e.g., "gpt-4o-mini")

    Returns:
        True if our brands were mentioned, False otherwise or on error

    Example:
        >>> appeared = _check_brands_appeared(
        ...     "./output/2025-11-02T08-00-00Z",
        ...     "email-warmup", "openai", "gpt-4o-mini"
        ... )
        >>> appeared
        True

    Note:
        This function handles all errors gracefully by returning False.
        Missing files, malformed JSON, or unexpected data structures are
        logged but don't crash the CLI.
    """
    try:
        parsed_filename = get_parsed_answer_filename(intent_id, provider, model_name)
        parsed_path = Path(output_dir) / parsed_filename

        if not parsed_path.exists():
            # Parsed file doesn't exist, assume no mentions
            return False

        with open(parsed_path, encoding="utf-8") as f:
            parsed_data = json.load(f)

        # Check if my_mentions list is non-empty (correct key from ExtractionResult)
        my_mentions = parsed_data.get("my_mentions", [])
        return bool(my_mentions)

    except json.JSONDecodeError as e:
        # Malformed JSON - log warning and return False
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Failed to parse JSON for {intent_id}/{provider}/{model_name}: {e}"
        )
        return False

    except OSError as e:
        # File read error - log warning and return False
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Failed to read parsed file for {intent_id}/{provider}/{model_name}: {e}"
        )
        return False

    except Exception as e:
        # Unexpected error - log warning and return False
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Unexpected error checking brand appearance for "
            f"{intent_id}/{provider}/{model_name}: {e}",
            exc_info=True,
        )
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
    # Suppress JSON logs in human mode (unless verbose=True)
    quiet_logs = output_mode.is_human()
    setup_logging(verbose=verbose, quiet_logs=quiet_logs)

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
                else nullcontext()
            ):
                results = run_all(runtime_config, progress_callback=progress_callback)

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


@app.command()
def eval(
    fixtures: Path = typer.Option(
        ...,
        "--fixtures",
        "-f",
        help="Path to YAML file containing evaluation test cases",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: 'text' (human-friendly) or 'json' (machine-readable)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable debug logging",
    ),
    save_results: bool = typer.Option(
        False,
        "--save-results",
        help="Save evaluation results to database for historical tracking",
    ),
):
    """
    Run evaluation suite to test extraction accuracy.

    This command runs the evaluation framework to validate that brand mention
    detection and rank extraction are working correctly. It's useful for:

    - Quality assurance before releases
    - Regression testing after code changes
    - Validation of extraction algorithms
    - Future Cloud deployment readiness

    The evaluation suite:
    - Loads test cases from YAML fixtures file
    - Runs brand mention detection and rank extraction
    - Computes precision, recall, F1 scores
    - Shows detailed results for each test case
    - Optionally saves results to database for historical tracking

    Exit codes:
      0: All test cases passed
      1: Configuration or file error
      2: Any test case failed

    Examples:
      # Run evaluation with default fixtures
      llm-answer-watcher eval --fixtures evals/testcases/fixtures.yaml

      # Run evaluation in JSON mode for automation
      llm-answer-watcher eval --fixtures evals/testcases/fixtures.yaml --format json

      # Run evaluation and save results to database
      llm-answer-watcher eval --fixtures evals/testcases/fixtures.yaml --save-results
    """
    # Set global output mode
    output_mode.format = format

    # Setup logging level
    # Suppress JSON logs in human mode (unless verbose=True)
    quiet_logs = output_mode.is_human()
    setup_logging(verbose=verbose, quiet_logs=quiet_logs)

    # Load and validate test fixtures
    try:
        with spinner("Loading test fixtures..."):
            # The run_eval_suite function will handle file loading and validation
            pass

        info(f"Loading evaluation suite from: {fixtures}")

    except Exception as e:
        error(f"Failed to load fixtures: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(EXIT_CONFIG_ERROR)

    # Run evaluation suite
    try:
        with spinner("Running evaluation suite..."):
            eval_results = run_eval_suite(fixtures)

        total_cases = eval_results["total_test_cases"]
        passed_cases = eval_results["total_passed"]
        failed_cases = total_cases - passed_cases
        pass_rate = eval_results["summary"]["pass_rate"]

        success(
            f"Evaluation completed: {passed_cases}/{total_cases} passed ({pass_rate:.1%})"
        )

        if failed_cases > 0:
            warning(f"{failed_cases} test case(s) failed")

        # Save results to database if requested
        if save_results:
            try:
                with spinner("Saving results to database..."):
                    # Initialize eval database
                    eval_db_path = "./output/evals/eval_results.db"
                    init_eval_db_if_needed(eval_db_path)

                    # Store results
                    import sqlite3

                    with sqlite3.connect(eval_db_path) as conn:
                        run_id = store_eval_results(conn, eval_results)
                        conn.commit()

                success(f"Results saved to database (run_id: {run_id})")
                info(f"Database: {eval_db_path}")
            except Exception as e:
                error(f"Failed to save results to database: {e}")
                if verbose:
                    import traceback

                    traceback.print_exc()
                # Don't exit on database save failure, just warn

    except FileNotFoundError as e:
        error(f"Fixtures file not found: {e}")
        raise typer.Exit(EXIT_CONFIG_ERROR)
    except ValueError as e:
        error(f"Invalid fixtures format: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(EXIT_CONFIG_ERROR)
    except Exception as e:
        error(f"Evaluation failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(EXIT_CONFIG_ERROR)

    # Display results in text mode
    if output_mode.is_human():
        info("\nDetailed Results:")
        for result in eval_results["results"]:
            status = "✅ PASS" if result.overall_passed else "❌ FAIL"
            info(f"  {status}: {result.test_description}")

            # Show critical metrics
            critical_metrics = [
                "mention_precision",
                "mention_recall",
                "mention_f1",
                "my_brands_coverage",
            ]
            for metric in result.metrics:
                if metric.name in critical_metrics:
                    status_icon = "✅" if metric.passed else "❌"
                    info(f"    {status_icon} {metric.name}: {metric.value:.3f}")

        # Show summary
        summary = eval_results["summary"]
        info("\nSummary:")
        info(f"  Pass rate: {summary['pass_rate']:.1%}")
        info(f"  Total cases: {summary['total_test_cases']}")
        info(f"  Passed: {summary['total_passed']}")
        info(f"  Failed: {summary['total_failed']}")

        # Show average scores
        if summary["average_scores"]:
            info("\nAverage Scores:")
            for metric_name, avg_score in summary["average_scores"].items():
                info(f"  {metric_name}: {avg_score:.3f}")

        # Show threshold check results
        if "threshold_check" in eval_results:
            threshold_check = eval_results["threshold_check"]
            threshold_summary = threshold_check["summary"]

            info("\nQuality Thresholds:")
            status_icon = (
                "✅" if threshold_summary["overall_status"] == "PASS" else "❌"
            )
            info(
                f"  {status_icon} Overall Status: {threshold_summary['overall_status']}"
            )
            info(
                f"  Pass Rate: {threshold_check['pass_rate']:.1%} (minimum: {threshold_summary['pass_rate_threshold']:.0%})"
            )
            info(
                f"  Violations: {threshold_summary['total_violations']} (critical: {threshold_summary['critical_violations']})"
            )

            # Show specific violations
            if threshold_check["threshold_violations"]:
                info("\nThreshold Violations:")
                for violation in threshold_check["threshold_violations"]:
                    severity_icon = (
                        "🔴" if violation["severity"] == "critical" else "🟡"
                    )
                    info(
                        f"  {severity_icon} {violation['metric']}: {violation['average']:.3f} "
                        f"(threshold: {violation['threshold']:.1f}, "
                        f"{violation['gap_percent']:.0f}% below)"
                    )
            else:
                info("  ✅ All quality thresholds met")

    # Display results in JSON mode
    elif output_mode.is_agent():
        # Build structured JSON output
        json_output = {
            "total_test_cases": eval_results["total_test_cases"],
            "total_passed": eval_results["total_passed"],
            "total_failed": eval_results["total_test_cases"]
            - eval_results["total_passed"],
            "pass_rate": eval_results["summary"]["pass_rate"],
            "average_scores": eval_results["summary"]["average_scores"],
            "results": [],
        }

        # Add detailed results for each test case
        for result in eval_results["results"]:
            result_dict = {
                "test_description": result.test_description,
                "overall_passed": result.overall_passed,
                "metrics": [
                    {
                        "name": metric.name,
                        "value": metric.value,
                        "passed": metric.passed,
                        "details": metric.details,
                    }
                    for metric in result.metrics
                ],
            }
            json_output["results"].append(result_dict)

        output_mode.add_json("evaluation_results", json_output)
        output_mode.flush_json()

    # Determine exit code based on threshold checking
    threshold_check = eval_results.get("threshold_check", {})

    if threshold_check.get("summary", {}).get("overall_status") == "FAIL":
        # Check if there are critical violations (my_brands_coverage below threshold)
        critical_violations = threshold_check.get("critical_violations", 0)
        if critical_violations > 0:
            # Critical quality failures - fail with code 2
            raise typer.Exit(2)  # Critical thresholds failed
        # Non-critical violations - fail with code 2 but could be warning in future
        raise typer.Exit(2)  # Quality thresholds not met
    if failed_cases > 0:
        # Some individual test cases failed but overall thresholds passed
        raise typer.Exit(2)  # Some tests failed
    raise typer.Exit(EXIT_SUCCESS)  # All tests passed and thresholds met


# Create prices command subapp
prices_app = typer.Typer(help="Manage LLM pricing data")
app.add_typer(prices_app, name="prices")


@prices_app.command("show")
def prices_show(
    provider: str = typer.Option(
        None,
        "--provider",
        "-p",
        help="Filter by provider (openai, anthropic, mistral, etc.)",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: 'text' or 'json'",
    ),
):
    """
    Display current pricing for LLM models.

    Shows cached pricing data from llm-prices.com with local overrides applied.
    Use 'prices refresh' to update pricing from remote source.

    Examples:
      # Show all pricing
      llm-answer-watcher prices show

      # Show only OpenAI models
      llm-answer-watcher prices show --provider openai

      # JSON output for automation
      llm-answer-watcher prices show --format json
    """
    from rich.console import Console
    from rich.table import Table

    from llm_answer_watcher.utils.pricing import list_available_models

    # Set output mode
    output_mode.format = format

    try:
        models = list_available_models()

        # Filter by provider if specified
        if provider:
            models = [m for m in models if m["provider"].lower() == provider.lower()]

        if not models:
            if format == "json":
                print(json.dumps({"models": [], "count": 0}))
            else:
                error(f"No models found for provider: {provider}")
            raise typer.Exit(1)

        # JSON output
        if format == "json":
            output = {"models": models, "count": len(models)}
            print(json.dumps(output, indent=2))
            raise typer.Exit(0)

        # Text output with Rich table
        console = Console()
        table = Table(title=f"LLM Pricing ({len(models)} models)")
        table.add_column("Provider", style="cyan")
        table.add_column("Model", style="yellow")
        table.add_column("Input ($/1M)", justify="right", style="green")
        table.add_column("Output ($/1M)", justify="right", style="green")
        table.add_column("Cached ($/1M)", justify="right", style="blue")
        table.add_column("Source", style="magenta")

        for model in models:
            cached = (
                f"${model['input_cached']:.2f}"
                if model.get("input_cached")
                else "N/A"
            )
            table.add_row(
                model["provider"],
                model["model"],
                f"${model['input']:.2f}",
                f"${model['output']:.2f}",
                cached,
                model["source"],
            )

        console.print(table)
        raise typer.Exit(0)

    except Exception as e:
        if format == "json":
            print(json.dumps({"error": str(e)}))
        else:
            error(f"Failed to show pricing: {e}")
        raise typer.Exit(1)


@prices_app.command("refresh")
def prices_refresh(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force refresh even if cache is fresh",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: 'text' or 'json'",
    ),
):
    """
    Refresh pricing data from llm-prices.com.

    Downloads latest pricing and updates the local cache (config/pricing_cache.json).
    Cache is valid for 24 hours; use --force to refresh earlier.

    Examples:
      # Refresh if cache is older than 24 hours
      llm-answer-watcher prices refresh

      # Force refresh now
      llm-answer-watcher prices refresh --force

      # JSON output
      llm-answer-watcher prices refresh --format json
    """
    from rich.console import Console

    from llm_answer_watcher.utils.pricing import refresh_pricing

    # Set output mode
    output_mode.format = format

    try:
        if format != "json":
            with spinner(
                "Refreshing pricing from llm-prices.com...", format != "json"
            ):
                result = refresh_pricing(force=force)
        else:
            result = refresh_pricing(force=force)

        # JSON output
        if format == "json":
            print(json.dumps(result, indent=2))
            raise typer.Exit(0)

        # Text output
        if result["status"] == "success":
            success(
                f"✓ Refreshed pricing for {result['model_count']} models "
                f"(updated: {result['updated_at']})"
            )
        elif result["status"] == "skipped":
            info(f"ℹ  {result['reason']}")
            info(
                f"   Cached {result['model_count']} models from {result['cached_at']}"
            )
        else:
            error(f"✗ Failed to refresh pricing: {result.get('error', 'Unknown error')}")
            raise typer.Exit(1)

        raise typer.Exit(0)

    except Exception as e:
        if format == "json":
            print(json.dumps({"status": "error", "error": str(e)}))
        else:
            error(f"Failed to refresh pricing: {e}")
        raise typer.Exit(1)


@prices_app.command("list")
def prices_list(
    provider: str = typer.Option(
        None,
        "--provider",
        "-p",
        help="Filter by provider",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: 'text' or 'json'",
    ),
):
    """
    List all supported models with pricing.

    Displays comprehensive list of all models from cache, overrides, and fallback pricing.
    Useful for finding model names and comparing costs.

    Examples:
      # List all models
      llm-answer-watcher prices list

      # List only Anthropic models
      llm-answer-watcher prices list --provider anthropic

      # JSON output for parsing
      llm-answer-watcher prices list --format json
    """
    # This is essentially the same as 'show' but explicitly named for discoverability
    prices_show(provider=provider, format=format)


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
        console.print("  eval      Run evaluation suite to test extraction accuracy")
        console.print("  prices    Manage LLM pricing data (show, refresh, list)")


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


if __name__ == "__main__":
    app()
