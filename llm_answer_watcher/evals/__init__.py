"""
Evaluation Framework for LLM Answer Watcher.

This module provides comprehensive evaluation capabilities to test pipeline correctness,
catch extraction regressions, and future-proof the product for Cloud deployment.
"""

from .schema import EvalTestCase, EvalMetricScore, EvalResult
from .runner import run_eval_suite
from .metrics import compute_mention_metrics, compute_rank_metrics

__all__ = [
    "EvalTestCase",
    "EvalMetricScore",
    "EvalResult",
    "run_eval_suite",
    "compute_mention_metrics",
    "compute_rank_metrics",
]