"""
Answer parsing and extraction orchestration for LLM Answer Watcher.

This module ties together brand mention detection and rank extraction into
a unified parsing pipeline. It processes raw LLM answers and produces
structured ExtractionResult objects with all signals extracted.

The parser:
1. Detects brand mentions (mine vs competitors) using mention_detector
2. Extracts ranked lists using rank_extractor (pattern or LLM-assisted)
3. Combines all signals into ExtractionResult for storage

Key features:
- Single entry point (parse_answer) for all extraction logic
- Structured output with all metadata
- Optional LLM-assisted extraction (disabled by default in v1)
- Comprehensive signal capture (appeared_mine, mentions, rankings)

Example:
    >>> from config.schema import Brands
    >>> brands = Brands(mine=["Warmly"], competitors=["HubSpot"])
    >>> result = parse_answer(
    ...     answer_text="I recommend 1. Warmly 2. HubSpot",
    ...     brands=brands,
    ...     intent_id="email-warmup",
    ...     provider="openai",
    ...     model_name="gpt-4o-mini",
    ...     timestamp_utc="2025-11-02T08:00:00Z"
    ... )
    >>> result.appeared_mine
    True
    >>> len(result.ranked_list)
    2
"""

from dataclasses import dataclass

from ..config.schema import Brands
from .mention_detector import BrandMention, detect_mentions
from .rank_extractor import (
    RankedBrand,
    extract_ranked_list_llm,
    extract_ranked_list_pattern,
)


@dataclass
class ExtractionResult:
    """
    Complete extraction result from LLM answer parsing.

    Contains all extracted signals: metadata, brand mentions, and rankings.
    Used for database storage and JSON artifact generation.

    Attributes:
        intent_id: Intent query identifier from config
        model_provider: LLM provider (e.g., "openai", "anthropic")
        model_name: Model identifier (e.g., "gpt-4o-mini")
        timestamp_utc: ISO 8601 timestamp when answer was parsed
        appeared_mine: True if any of our brands were mentioned
        my_mentions: List of mentions for our brands
        competitor_mentions: List of mentions for competitor brands
        ranked_list: Extracted ranked brands (if ranking structure detected)
        rank_extraction_method: Method used ("pattern" or "llm")
        rank_confidence: Overall confidence in ranking (0.0-1.0)
    """

    intent_id: str
    model_provider: str
    model_name: str
    timestamp_utc: str
    appeared_mine: bool
    my_mentions: list[BrandMention]
    competitor_mentions: list[BrandMention]
    ranked_list: list[RankedBrand]
    rank_extraction_method: str
    rank_confidence: float

    def __post_init__(self):
        """Validate rank_extraction_method."""
        if self.rank_extraction_method not in ("pattern", "llm"):
            raise ValueError(
                f"rank_extraction_method must be 'pattern' or 'llm', "
                f"got: {self.rank_extraction_method}"
            )


def parse_answer(
    answer_text: str,
    brands: Brands,
    intent_id: str,
    provider: str,
    model_name: str,
    timestamp_utc: str,
    use_llm_extraction: bool = False,
    llm_client: object | None = None,
) -> ExtractionResult:
    """
    Parse LLM answer and extract all signals.

    Orchestrates mention detection and rank extraction to produce a complete
    ExtractionResult with all structured data extracted from the answer.

    Processing pipeline:
    1. Detect brand mentions (mine vs competitors)
    2. Extract ranked list (pattern-based or LLM-assisted)
    3. Build ExtractionResult with all signals

    Args:
        answer_text: Raw LLM response text to parse
        brands: Brand configuration (mine + competitors)
        intent_id: Intent query identifier from config
        provider: LLM provider name (e.g., "openai", "anthropic")
        model_name: Model identifier (e.g., "gpt-4o-mini")
        timestamp_utc: ISO 8601 timestamp for this parse operation
        use_llm_extraction: If True, use LLM-assisted rank extraction (default: False)
        llm_client: LLM client for LLM-assisted extraction (required if use_llm_extraction=True)

    Returns:
        ExtractionResult with all extracted signals and metadata

    Raises:
        ValueError: If use_llm_extraction=True but llm_client=None

    Example:
        >>> from config.schema import Brands
        >>> brands = Brands(mine=["Warmly"], competitors=["HubSpot", "Instantly"])
        >>> text = "I recommend:\\n1. Warmly\\n2. HubSpot\\n3. Instantly"
        >>> result = parse_answer(
        ...     answer_text=text,
        ...     brands=brands,
        ...     intent_id="email-warmup",
        ...     provider="openai",
        ...     model_name="gpt-4o-mini",
        ...     timestamp_utc="2025-11-02T08:00:00Z"
        ... )
        >>> result.appeared_mine
        True
        >>> result.ranked_list[0].brand_name
        'Warmly'
        >>> result.rank_confidence
        1.0

    Note:
        - Mention detection uses word-boundary matching to avoid false positives
        - Rank extraction tries multiple patterns (numbered, bullets, headers)
        - LLM-assisted extraction is a stub in v1 (falls back to pattern-based)
    """
    # Validate LLM extraction parameters
    if use_llm_extraction and llm_client is None:
        raise ValueError("llm_client required when use_llm_extraction=True")

    # Step 1: Detect brand mentions
    all_mentions = detect_mentions(
        answer_text=answer_text,
        our_brands=brands.mine,
        competitor_brands=brands.competitors,
    )

    # Step 2: Separate mentions into mine vs competitors
    my_mentions = [m for m in all_mentions if m.brand_category == "mine"]
    competitor_mentions = [m for m in all_mentions if m.brand_category == "competitor"]

    # Step 3: Determine if our brand appeared
    appeared_mine = len(my_mentions) > 0

    # Step 4: Extract ranked list
    # Combine all brands for ranking (both mine and competitors)
    all_brands = brands.mine + brands.competitors

    if use_llm_extraction and llm_client is not None:
        # Use LLM-assisted extraction (v1 stub - falls back to pattern)
        ranked_list, rank_confidence = extract_ranked_list_llm(
            text=answer_text,
            known_brands=all_brands,
            client=llm_client,
        )
        rank_method = "llm"
    else:
        # Use pattern-based extraction (default)
        ranked_list, rank_confidence = extract_ranked_list_pattern(
            text=answer_text,
            known_brands=all_brands,
        )
        rank_method = "pattern"

    # Step 5: Build ExtractionResult
    return ExtractionResult(
        intent_id=intent_id,
        model_provider=provider,
        model_name=model_name,
        timestamp_utc=timestamp_utc,
        appeared_mine=appeared_mine,
        my_mentions=my_mentions,
        competitor_mentions=competitor_mentions,
        ranked_list=ranked_list,
        rank_extraction_method=rank_method,
        rank_confidence=rank_confidence,
    )
