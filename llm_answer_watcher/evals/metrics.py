"""
Evaluation metrics for the LLM Answer Watcher evaluation framework.

This module provides functions to compute various metrics that measure the
accuracy and quality of brand mention detection and rank extraction.
"""

from .schema import EvalMetricScore, EvalTestCase


def compute_mention_metrics(
    test_case: EvalTestCase, actual_mentions: list[str]
) -> list[EvalMetricScore]:
    """
    Compute mention detection metrics (precision, recall, F1).

    Args:
        test_case: The test case with expected mentions
        actual_mentions: List of mentions actually detected by the system

    Returns:
        List of metric scores for mention detection
    """
    # Combine all expected mentions (my brands + competitors)
    expected_mentions = set(
        test_case.expected_my_mentions + test_case.expected_competitor_mentions
    )
    actual_mentions_set = set(actual_mentions)

    # Calculate true positives, false positives, false negatives
    true_positives = expected_mentions.intersection(actual_mentions_set)
    false_positives = actual_mentions_set - expected_mentions
    false_negatives = expected_mentions - actual_mentions_set

    # Compute precision, recall, F1
    precision = (
        len(true_positives) / len(actual_mentions_set) if actual_mentions_set else 0.0
    )
    recall = len(true_positives) / len(expected_mentions) if expected_mentions else 0.0
    f1 = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    # Create metric scores with passing thresholds
    metrics = [
        EvalMetricScore(
            name="mention_precision",
            value=precision,
            passed=precision >= 0.8,  # 80% precision threshold
            details={
                "true_positives": len(true_positives),
                "false_positives": len(false_positives),
                "expected_mentions": list(expected_mentions),
                "actual_mentions": list(actual_mentions_set),
            },
        ),
        EvalMetricScore(
            name="mention_recall",
            value=recall,
            passed=recall >= 0.8,  # 80% recall threshold
            details={
                "true_positives": len(true_positives),
                "false_negatives": len(false_negatives),
                "expected_mentions": list(expected_mentions),
                "actual_mentions": list(actual_mentions_set),
            },
        ),
        EvalMetricScore(
            name="mention_f1",
            value=f1,
            passed=f1 >= 0.8,  # 80% F1 threshold
            details={
                "precision": precision,
                "recall": recall,
                "f1_formula": "2 * (precision * recall) / (precision + recall)",
            },
        ),
    ]

    return metrics


def compute_rank_metrics(
    test_case: EvalTestCase, actual_ranked_list: list[str]
) -> list[EvalMetricScore]:
    """
    Compute ranking metrics (position accuracy, list similarity).

    Args:
        test_case: The test case with expected ranked list
        actual_ranked_list: List of brands actually extracted in rank order

    Returns:
        List of metric scores for rank extraction
    """
    expected_ranked = test_case.expected_ranked_list
    actual_ranked_trimmed = actual_ranked_list[
        : len(expected_ranked)
    ]  # Compare same length

    # Compute position accuracy (how many items are in correct position)
    correct_positions = sum(
        1
        for i, (exp, act) in enumerate(
            zip(expected_ranked, actual_ranked_trimmed, strict=False)
        )
        if exp == act
    )
    position_accuracy = (
        correct_positions / len(expected_ranked) if expected_ranked else 1.0
    )

    # Compute list overlap (Jaccard similarity)
    expected_set = set(expected_ranked)
    actual_set = set(actual_ranked_list)
    intersection = expected_set.intersection(actual_set)
    union = expected_set.union(actual_set)
    jaccard_similarity = len(intersection) / len(union) if union else 1.0

    # Compute rank correlation (Spearman's footrule distance approximation)
    # For each item, measure how far it is from its expected position
    rank_displacement = 0
    max_possible_displacement = 0

    for i, expected_item in enumerate(expected_ranked):
        if expected_item in actual_ranked_list:
            actual_position = actual_ranked_list.index(expected_item)
            displacement = abs(i - actual_position)
            rank_displacement += displacement
        else:
            # Missing items get maximum penalty
            rank_displacement += len(expected_ranked)

        max_possible_displacement += len(expected_ranked)

    # Normalize to 0-1 scale (1.0 = perfect ranking)
    rank_correlation = (
        1.0 - (rank_displacement / max_possible_displacement)
        if max_possible_displacement > 0
        else 1.0
    )

    metrics = [
        EvalMetricScore(
            name="rank_position_accuracy",
            value=position_accuracy,
            passed=position_accuracy >= 0.7,  # 70% position accuracy threshold
            details={
                "correct_positions": correct_positions,
                "total_positions": len(expected_ranked),
                "expected_ranked": expected_ranked,
                "actual_ranked_trimmed": actual_ranked_trimmed,
            },
        ),
        EvalMetricScore(
            name="rank_list_overlap",
            value=jaccard_similarity,
            passed=jaccard_similarity >= 0.8,  # 80% overlap threshold
            details={
                "intersection_size": len(intersection),
                "union_size": len(union),
                "expected_set": list(expected_set),
                "actual_set": list(actual_set),
            },
        ),
        EvalMetricScore(
            name="rank_correlation",
            value=rank_correlation,
            passed=rank_correlation >= 0.6,  # 60% correlation threshold (more lenient)
            details={
                "rank_displacement": rank_displacement,
                "max_possible_displacement": max_possible_displacement,
                "correlation_formula": "1.0 - (displacement / max_displacement)",
            },
        ),
    ]

    return metrics


def compute_completeness_metrics(
    test_case: EvalTestCase, actual_mentions: list[str]
) -> list[EvalMetricScore]:
    """
    Compute completeness metrics (brand coverage, competitor detection).

    Args:
        test_case: The test case with brand definitions
        actual_mentions: List of mentions actually detected

    Returns:
        List of metric scores for completeness assessment
    """
    actual_mentions_set = set(actual_mentions)

    # Check coverage of my brands (compare against expected mentions, not all aliases)
    expected_my_mentions_set = set(test_case.expected_my_mentions)
    my_brands_detected = expected_my_mentions_set.intersection(actual_mentions_set)
    my_brands_coverage = (
        len(my_brands_detected) / len(expected_my_mentions_set)
        if expected_my_mentions_set
        else 1.0
    )

    # Check detection of competitors (compare against expected mentions, not all aliases)
    expected_competitor_mentions_set = set(test_case.expected_competitor_mentions)
    competitors_detected = expected_competitor_mentions_set.intersection(
        actual_mentions_set
    )
    competitors_coverage = (
        len(competitors_detected) / len(expected_competitor_mentions_set)
        if expected_competitor_mentions_set
        else 1.0
    )

    # Overall brand coverage (all expected mentions)
    all_expected_mentions = expected_my_mentions_set.union(
        expected_competitor_mentions_set
    )
    all_detected = all_expected_mentions.intersection(actual_mentions_set)
    overall_coverage = (
        len(all_detected) / len(all_expected_mentions) if all_expected_mentions else 1.0
    )

    metrics = [
        EvalMetricScore(
            name="my_brands_coverage",
            value=my_brands_coverage,
            passed=my_brands_coverage >= 0.9,  # 90% coverage for my brands (critical)
            details={
                "my_brands_detected": len(my_brands_detected),
                "total_expected_my_mentions": len(expected_my_mentions_set),
                "expected_my_mentions": list(expected_my_mentions_set),
                "detected_my_mentions": list(my_brands_detected),
            },
        ),
        EvalMetricScore(
            name="competitors_coverage",
            value=competitors_coverage,
            passed=competitors_coverage
            >= 0.7,  # 70% coverage for competitors (important but less critical)
            details={
                "competitors_detected": len(competitors_detected),
                "total_expected_competitor_mentions": len(
                    expected_competitor_mentions_set
                ),
                "expected_competitor_mentions": list(expected_competitor_mentions_set),
                "detected_competitor_mentions": list(competitors_detected),
            },
        ),
        EvalMetricScore(
            name="overall_brand_coverage",
            value=overall_coverage,
            passed=overall_coverage >= 0.8,  # 80% overall coverage
            details={
                "all_detected": len(all_detected),
                "total_expected_mentions": len(all_expected_mentions),
                "all_expected_mentions": list(all_expected_mentions),
                "all_detected_mentions": list(all_detected),
            },
        ),
    ]

    return metrics
