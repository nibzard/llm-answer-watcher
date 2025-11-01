"""
Cost estimation utilities for LLM Answer Watcher.

Estimates USD costs based on provider pricing and token usage.
Pricing data is hardcoded based on public provider pricing as of the
update date. Users should verify costs on their provider's billing dashboard.

This module provides:
- PRICING: Public pricing table for all supported providers/models
- estimate_cost: Calculate estimated cost from token usage metadata

Important:
    Cost estimates are approximate and based on public pricing as of the
    update date. Actual costs may vary. Always check your provider's
    billing dashboard for accurate costs.

Example:
    >>> from utils.cost import estimate_cost
    >>> usage = {"prompt_tokens": 100, "completion_tokens": 50}
    >>> cost = estimate_cost("openai", "gpt-4o-mini", usage)
    >>> print(f"${cost:.6f}")
    $0.000045
"""

import logging

# Pricing table based on public provider pricing
# Updated: 2025-11-01
# All prices are USD per token (calculated as price_per_million / 1,000,000)
PRICING = {
    "openai": {
        "gpt-4o-mini": {
            "input": 0.150 / 1_000_000,  # $0.15 per 1M input tokens
            "output": 0.600 / 1_000_000,  # $0.60 per 1M output tokens
        },
        "gpt-4o": {
            "input": 2.50 / 1_000_000,  # $2.50 per 1M input tokens
            "output": 10.00 / 1_000_000,  # $10.00 per 1M output tokens
        },
        "gpt-4o-2024-11-20": {
            "input": 2.50 / 1_000_000,
            "output": 10.00 / 1_000_000,
        },
        "gpt-4o-2024-08-06": {
            "input": 2.50 / 1_000_000,
            "output": 10.00 / 1_000_000,
        },
        "gpt-4o-2024-05-13": {
            "input": 5.00 / 1_000_000,
            "output": 15.00 / 1_000_000,
        },
        "gpt-4-turbo": {
            "input": 10.00 / 1_000_000,
            "output": 30.00 / 1_000_000,
        },
        "gpt-4": {
            "input": 30.00 / 1_000_000,
            "output": 60.00 / 1_000_000,
        },
        "gpt-3.5-turbo": {
            "input": 0.50 / 1_000_000,
            "output": 1.50 / 1_000_000,
        },
    },
    "anthropic": {
        "claude-3-5-haiku-20241022": {
            "input": 0.80 / 1_000_000,  # $0.80 per 1M input tokens
            "output": 4.00 / 1_000_000,  # $4.00 per 1M output tokens
        },
        "claude-3-5-sonnet-20241022": {
            "input": 3.00 / 1_000_000,  # $3.00 per 1M input tokens
            "output": 15.00 / 1_000_000,  # $15.00 per 1M output tokens
        },
        "claude-3-5-sonnet-20240620": {
            "input": 3.00 / 1_000_000,
            "output": 15.00 / 1_000_000,
        },
        "claude-3-opus-20240229": {
            "input": 15.00 / 1_000_000,
            "output": 75.00 / 1_000_000,
        },
        "claude-3-sonnet-20240229": {
            "input": 3.00 / 1_000_000,
            "output": 15.00 / 1_000_000,
        },
        "claude-3-haiku-20240307": {
            "input": 0.25 / 1_000_000,
            "output": 1.25 / 1_000_000,
        },
    },
    "mistral": {
        "mistral-large-latest": {
            "input": 2.00 / 1_000_000,
            "output": 6.00 / 1_000_000,
        },
        "mistral-small-latest": {
            "input": 0.20 / 1_000_000,
            "output": 0.60 / 1_000_000,
        },
        "codestral-latest": {
            "input": 0.20 / 1_000_000,
            "output": 0.60 / 1_000_000,
        },
    },
}

# Get logger for this module
logger = logging.getLogger(__name__)


def estimate_cost(provider: str, model: str, usage_meta: dict) -> float:
    """
    Estimate cost in USD based on token usage and provider pricing.

    Looks up pricing for the provider/model combination and calculates
    cost based on prompt_tokens (input) and completion_tokens (output)
    from the usage metadata dictionary.

    Returns 0.0 if pricing is unavailable (with warning logged).

    Args:
        provider: Provider name (e.g., "openai", "anthropic", "mistral")
        model: Model identifier (e.g., "gpt-4o-mini", "claude-3-5-haiku-20241022")
        usage_meta: Dictionary containing token usage with keys:
            - "prompt_tokens" (int): Number of input tokens
            - "completion_tokens" (int): Number of output tokens
            Other keys are ignored.

    Returns:
        float: Estimated cost in USD, rounded to 6 decimal places.
               Returns 0.0 if pricing data is unavailable.

    Examples:
        >>> usage = {"prompt_tokens": 100, "completion_tokens": 50}
        >>> cost = estimate_cost("openai", "gpt-4o-mini", usage)
        >>> cost
        0.000045

        >>> # Cost = (100 * $0.15/1M) + (50 * $0.60/1M)
        >>> # Cost = $0.000015 + $0.000030 = $0.000045

        >>> # Unknown model returns 0.0 with warning
        >>> cost = estimate_cost("openai", "unknown-model", usage)
        >>> cost
        0.0

        >>> # Claude example
        >>> usage = {"prompt_tokens": 1000, "completion_tokens": 500}
        >>> cost = estimate_cost("anthropic", "claude-3-5-haiku-20241022", usage)
        >>> cost
        0.002800

    Note:
        - Costs are estimates based on public pricing (updated 2025-11-01)
        - Actual costs may vary due to volume discounts, special pricing, etc.
        - Always verify costs on your provider's billing dashboard
        - Missing token counts default to 0 (graceful handling)
        - Logs warning if pricing data unavailable for provider/model

    Warning:
        This function NEVER logs API keys or sensitive data.
        Only provider name and model name are logged in warnings.
    """
    # Look up pricing for provider and model
    pricing = PRICING.get(provider, {}).get(model)

    if not pricing:
        # Pricing unavailable - log warning and return 0.0
        available_providers = list(PRICING.keys())
        logger.warning(
            f"Pricing unavailable for provider='{provider}', model='{model}'. "
            f"Returning $0.00 cost estimate. Available providers: {available_providers}"
        )
        return 0.0

    # Extract token counts (default to 0 if missing)
    input_tokens = usage_meta.get("prompt_tokens", 0)
    output_tokens = usage_meta.get("completion_tokens", 0)

    # Calculate cost: (input tokens * input price) + (output tokens * output price)
    cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

    # Round to 6 decimal places for consistency
    return round(cost, 6)
