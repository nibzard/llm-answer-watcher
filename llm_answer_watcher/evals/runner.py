"""
Evaluation runner for the LLM Answer Watcher evaluation framework.

This module provides the main orchestrator function `run_eval_suite()` that
loads test cases, executes the evaluation pipeline, and returns results.
"""

import yaml
from pathlib import Path
from typing import Any

from ..extractor.mention_detector import MentionDetector
from ..extractor.rank_extractor import RankExtractor
from .schema import EvalTestCase, EvalResult
from .metrics import compute_mention_metrics, compute_rank_metrics, compute_completeness_metrics


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

    with open(fixtures_path, 'r', encoding='utf-8') as f:
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
    mention_detector: MentionDetector,
    rank_extractor: RankExtractor,
) -> EvalResult:
    """
    Evaluate a single test case using the provided extractors.

    Args:
        test_case: The test case to evaluate
        mention_detector: Configured mention detector instance
        rank_extractor: Configured rank extractor instance

    Returns:
        EvalResult containing all computed metrics for this test case
    """
    # Detect brand mentions
    mention_result = mention_detector.extract_mentions(
        text=test_case.llm_answer_text,
        my_brands=test_case.brands_mine,
        competitor_brands=test_case.brands_competitors,
    )

    # Extract ranked list
    rank_result = rank_extractor.extract_ranked_list(
        text=test_case.llm_answer_text,
        my_brands=test_case.brands_mine,
        competitor_brands=test_case.brands_competitors,
    )

    # Gather all detected mentions for metrics computation
    actual_mentions = []
    if mention_result.my_mentions:
        actual_mentions.extend(mention_result.my_mentions)
    if mention_result.competitor_mentions:
        actual_mentions.extend(mention_result.competitor_mentions)

    # Compute all metric categories
    mention_metrics = compute_mention_metrics(test_case, actual_mentions)
    rank_metrics = compute_rank_metrics(test_case, rank_result.ranked_list)
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
    mention_detector: MentionDetector | None = None,
    rank_extractor: RankExtractor | None = None,
) -> dict[str, Any]:
    """
    Run the complete evaluation suite on all test cases.

    This is the main entry point for the evaluation framework. It loads test cases,
    runs them through the extraction pipeline, computes metrics, and returns
    comprehensive results.

    Args:
        fixtures_path: Path to YAML file containing test cases
        mention_detector: Optional pre-configured mention detector
        rank_extractor: Optional pre-configured rank extractor

    Returns:
        Dictionary containing:
        - 'results': List of EvalResult objects for each test case
        - 'summary': Overall statistics (pass rate, average scores, etc.)
        - 'total_test_cases': Number of test cases evaluated
        - 'total_passed': Number of test cases that passed overall
    """
    # Load test cases
    test_cases = load_test_cases(fixtures_path)

    # Initialize extractors if not provided
    if mention_detector is None:
        mention_detector = MentionDetector()
    if rank_extractor is None:
        rank_extractor = RankExtractor()

    # Evaluate each test case
    results = []
    for test_case in test_cases:
        try:
            result = evaluate_single_test_case(test_case, mention_detector, rank_extractor)
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