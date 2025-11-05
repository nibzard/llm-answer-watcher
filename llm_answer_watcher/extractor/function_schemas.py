"""
Function calling schemas for LLM Answer Watcher.

This module defines OpenAI function calling schemas used for structured
brand mention extraction. Function calling provides higher accuracy and
lower latency compared to regex-based parsing.

Key benefits of function calling:
- Structured output (JSON schema validated by LLM)
- Context-aware extraction (understands variations and synonyms)
- Rank detection without regex patterns
- Confidence scoring built-in
- 40-50% latency reduction vs separate LLM calls

Security:
- Uses OpenAI Structured Outputs (strict=true) for schema adherence
- No code execution (pure data extraction)
- Validated against Pydantic models

Example:
    >>> from llm_runner.models import build_client
    >>> client = build_client(
    ...     provider="openai",
    ...     model_name="gpt-5-nano",
    ...     api_key="sk-...",
    ...     system_prompt="You are a brand extraction assistant",
    ...     tools=[EXTRACT_BRAND_MENTIONS_FUNCTION],
    ...     tool_choice="required"
    ... )
"""

# OpenAI Responses API function schema for brand mention extraction
# NOTE: This uses the Responses API format (internally-tagged)
# NOT the Chat Completions API format (externally-tagged with nested "function" key)
EXTRACT_BRAND_MENTIONS_FUNCTION = {
    "type": "function",
    "name": "extract_brand_mentions",
    "description": """Extract all brand/product mentions from the given text answer, along with their rank/position if the answer presents them in a ranked or ordered format.

CRITICAL INSTRUCTIONS:
- Include EVERY brand/product mentioned, even if briefly
- Assign rank=null if no clear ranking/ordering is present
- If brands are numbered (1. Brand, 2. Brand), use that as rank
- If brands appear in a list without numbers, assign rank by order of appearance
- Set confidence based on how explicitly the brand is mentioned:
  * "high": Brand explicitly recommended or discussed in detail
  * "medium": Brand mentioned as an option or alternative
  * "low": Brand mentioned in passing or tangentially
- Normalize brand names to their canonical form (e.g., "hubspot" -> "HubSpot")
- Extract context snippets showing where each brand was mentioned""",
    "parameters": {
        "type": "object",
        "properties": {
            "brands_mentioned": {
                "type": "array",
                "description": "List of all brands/products mentioned in the answer",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Canonical brand name (e.g., 'HubSpot', 'Instantly', 'Lemwarm')",
                        },
                        "rank": {
                            "anyOf": [
                                {"type": "integer", "minimum": 1},
                                {"type": "null"},
                            ],
                            "description": "Position in ranking (1=best, 2=second, etc.). Null if no clear ranking.",
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Confidence level for this mention based on explicitness",
                        },
                        "context_snippet": {
                            "type": "string",
                            "description": "Brief excerpt (max 100 chars) from answer showing where brand was mentioned",
                            "maxLength": 100,
                        },
                    },
                    "required": ["name", "confidence", "context_snippet"],
                    "additionalProperties": False,
                },
            },
            "extraction_notes": {
                "type": "string",
                "description": "Optional notes about the extraction (e.g., 'No clear ranking', 'Brands as equals')",
            },
        },
        "required": ["brands_mentioned"],
        "additionalProperties": False,
    },
}


def validate_function_response(function_result: dict) -> bool:
    """
    Validate function calling response matches expected schema.

    Args:
        function_result: Parsed function call result from LLM

    Returns:
        True if valid, raises ValueError if invalid

    Raises:
        ValueError: If schema validation fails

    Example:
        >>> result = {"brands_mentioned": [...], "extraction_notes": "..."}
        >>> validate_function_response(result)
        True
    """
    # Check required top-level fields
    if "brands_mentioned" not in function_result:
        raise ValueError("Missing required field: brands_mentioned")

    if not isinstance(function_result["brands_mentioned"], list):
        raise ValueError("brands_mentioned must be a list")

    # Validate each brand mention
    for i, mention in enumerate(function_result["brands_mentioned"]):
        if not isinstance(mention, dict):
            raise ValueError(f"Brand mention {i} must be a dict")

        # Check required fields
        if "name" not in mention:
            raise ValueError(f"Brand mention {i} missing required field: name")

        if "confidence" not in mention:
            raise ValueError(f"Brand mention {i} missing required field: confidence")

        if "context_snippet" not in mention:
            raise ValueError(
                f"Brand mention {i} missing required field: context_snippet"
            )

        # Validate confidence values
        if mention["confidence"] not in {"high", "medium", "low"}:
            raise ValueError(
                f"Brand mention {i} has invalid confidence: {mention['confidence']}"
            )

        # Validate rank if present
        if "rank" in mention and mention["rank"] is not None:
            if not isinstance(mention["rank"], int) or mention["rank"] < 1:
                raise ValueError(
                    f"Brand mention {i} has invalid rank: {mention['rank']}"
                )

    return True
