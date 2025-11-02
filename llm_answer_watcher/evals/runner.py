"""
Evaluation runner for the LLM Answer Watcher evaluation framework.

This module provides the main orchestrator function `run_eval_suite()` that
loads test cases, executes the evaluation pipeline, and returns results.
"""

import sqlite3
from pathlib import Path
from typing import Any

import yaml

from ..extractor.mention_detector import detect_mentions
from ..extractor.rank_extractor import extract_ranked_list_pattern
from ..storage.eval_db import init_eval_db_if_needed, store_eval_results
from .metrics import (
    compute_completeness_metrics,
    compute_mention_metrics,
    compute_rank_metrics,
)
from .schema import EvalResult, EvalTestCase


def load_test_cases(fixtures_path: str | Path) -> list[EvalTestCase]:
    """
    Load test cases from a YAML fixtures file.

    Args:
        fixtures_path: Path to the YAML file containing test cases

    Returns:
        List of EvalTestCase objects loaded from the file

    Raises:
        FileNotFoundError: If the fixtures file doesn't exist
        yaml.YAMLError: If the YAML file is malformed
        ValueError: If test case validation fails
    """
    fixtures_path = Path(fixtures_path)

    if not fixtures_path.exists():
        raise FileNotFoundError(f"Test fixtures file not found: {fixtures_path}")

    with open(fixtures_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not data or 'test_cases' not in data:
        raise ValueError("Invalid fixtures file: must contain 'test_cases' key")

    test_cases = []
    for i, case_data in enumerate(data['test_cases']):
        try:
            test_case = EvalTestCase(**case_data)
            test_cases.append(test_case)
        except Exception as e:
            raise ValueError(f"Invalid test case at index {i}: {e}")

    return test_cases


def evaluate_single_test_case(
    test_case: EvalTestCase,
) -> EvalResult:
    """
    Evaluate a single test case using the extraction functions.

    Args:
        test_case: The test case to evaluate

    Returns:
        EvalResult containing all computed metrics for this test case
    """
    # Detect brand mentions
    mention_result = detect_mentions(
        answer_text=test_case.llm_answer_text,
        our_brands=test_case.brands_mine,
        competitor_brands=test_case.brands_competitors,
    )

    # Extract ranked list
    all_brands = test_case.brands_mine + test_case.brands_competitors
    rank_result, confidence = extract_ranked_list_pattern(
        text=test_case.llm_answer_text,
        known_brands=all_brands,
    )

    # Gather all detected mentions for metrics computation
    actual_mentions = mention_result

    # Compute all metric categories
    mention_metrics = compute_mention_metrics(test_case, actual_mentions)
    rank_metrics = compute_rank_metrics(test_case, rank_result)
    completeness_metrics = compute_completeness_metrics(test_case, actual_mentions)

    # Combine all metrics
    all_metrics = mention_metrics + rank_metrics + completeness_metrics

    # Determine overall pass status (all critical metrics must pass)
    critical_metric_names = {"mention_precision", "mention_recall", "mention_f1", "my_brands_coverage"}
    critical_metrics = [m for m in all_metrics if m.name in critical_metric_names]
    overall_passed = all(m.passed for m in critical_metrics)

    return EvalResult(
        test_description=test_case.description,
        metrics=all_metrics,
        overall_passed=overall_passed,
    )


def run_eval_suite(
    fixtures_path: str | Path,
) -> dict[str, Any]:
    """
    Run the complete evaluation suite on all test cases.

    This is the main entry point for the evaluation framework. It loads test cases,
    runs them through the extraction pipeline, computes metrics, and returns
    comprehensive results.

    Args:
        fixtures_path: Path to YAML file containing test cases

    Returns:
        Dictionary containing:
        - 'results': List of EvalResult objects for each test case
        - 'summary': Overall statistics (pass rate, average scores, etc.)
        - 'total_test_cases': Number of test cases evaluated
        - 'total_passed': Number of test cases that passed overall
    """
    # Load test cases
    test_cases = load_test_cases(fixtures_path)

    # Evaluate each test case
    results = []
    for test_case in test_cases:
        try:
            result = evaluate_single_test_case(test_case)
            results.append(result)
        except Exception as e:
            # Create a failure result for test cases that throw exceptions
            failure_result = EvalResult(
                test_description=test_case.description,
                metrics=[],
                overall_passed=False,
            )
            # Note: In a real implementation, you might want to include the error
            # information in the result, but the current schema doesn't support it
            results.append(failure_result)

    # Compute summary statistics
    total_test_cases = len(results)
    total_passed = sum(1 for r in results if r.overall_passed)
    pass_rate = total_passed / total_test_cases if total_test_cases > 0 else 0.0

    # Compute average scores for each metric type
    metric_scores = {}
    metric_counts = {}

    for result in results:
        for metric in result.metrics:
            if metric.name not in metric_scores:
                metric_scores[metric.name] = 0.0
                metric_counts[metric.name] = 0
            metric_scores[metric.name] += metric.value
            metric_counts[metric.name] += 1

    average_scores = {
        name: metric_scores[name] / metric_counts[name]
        for name in metric_scores
    }

    summary = {
        "pass_rate": pass_rate,
        "average_scores": average_scores,
        "total_test_cases": total_test_cases,
        "total_passed": total_passed,
        "total_failed": total_test_cases - total_passed,
    }

    return {
        "results": results,
        "summary": summary,
        "total_test_cases": total_test_cases,
        "total_passed": total_passed,
    }


def write_eval_results(
    eval_run_id: str,
    results: list[EvalResult],
    db_path: str,
) -> str:
    """
    Write evaluation results to the SQLite database for persistent storage.

    This function bridges the eval runner results with the database storage
    system, inserting both the run summary and detailed metric results.

    Args:
        eval_run_id: Unique identifier for this evaluation run
        results: List of EvalResult objects from run_eval_suite()
        db_path: Path to the SQLite database file for storage

    Returns:
        str: The run_id that was used for storage (same as input eval_run_id)

    Raises:
        sqlite3.Error: If database operation fails
        ValueError: If results are invalid or missing
        OSError: If database file cannot be created/accessed

    Example:
        >>> results = run_eval_suite("fixtures.yaml")
        >>> write_eval_results("2025-11-02T08-00-00Z", results["results"], "./eval_results.db")
        '2025-11-02T08-00-00Z'

    Security:
        - Uses parameterized queries via storage.eval_db functions
        - No SQL injection vulnerabilities
        - Database operations are wrapped in transactions

    Note:
        This function:
        1. Initializes the database if needed (creates tables, applies migrations)
        2. Creates the eval_results dictionary in the format expected by store_eval_results()
        3. Stores results atomically in a single transaction
        4. Returns the run_id for reference
    """
    if not eval_run_id:
        raise ValueError("eval_run_id cannot be empty")

    if not results:
        raise ValueError("results list cannot be empty")

    # Initialize database if needed (creates tables, applies migrations)
    init_eval_db_if_needed(db_path)

    # Convert EvalResult objects to the format expected by store_eval_results()
    # First, compute summary statistics from the results
    total_test_cases = len(results)
    total_passed = sum(1 for r in results if r.overall_passed)
    total_failed = total_test_cases - total_passed
    pass_rate = total_passed / total_test_cases if total_test_cases > 0 else 0.0

    # Compute average scores for each metric type
    metric_scores = {}
    metric_counts = {}

    for result in results:
        for metric in result.metrics:
            if metric.name not in metric_scores:
                metric_scores[metric.name] = 0.0
                metric_counts[metric.name] = 0
            metric_scores[metric.name] += metric.value
            metric_counts[metric.name] += 1

    average_scores = {
        name: metric_scores[name] / metric_counts[name]
        for name in metric_scores
    }

    # Create summary dictionary
    summary = {
        "pass_rate": pass_rate,
        "average_scores": average_scores,
        "total_test_cases": total_test_cases,
        "total_passed": total_passed,
        "total_failed": total_failed,
    }

    # Create eval_results dictionary in the expected format
    eval_results_dict = {
        "results": results,
        "summary": summary,
        "total_test_cases": total_test_cases,
        "total_passed": total_passed,
    }

    # Store results in database
    with sqlite3.connect(db_path) as conn:
        run_id = store_eval_results(conn, eval_results_dict, eval_run_id)
        conn.commit()

    return run_id
