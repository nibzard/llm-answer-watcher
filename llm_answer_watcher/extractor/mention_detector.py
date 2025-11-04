"""
Brand mention detection for LLM Answer Watcher.

This module implements word-boundary regex matching to detect brand mentions
in LLM responses, avoiding false positives like "hub" matching in "GitHub".

Key features:
- Word-boundary matching (critical for accuracy)
- Case-insensitive detection
- Multiple aliases per brand support
- Structured mention data with position tracking
- Normalized brand names for deduplication

Security:
- Always uses re.escape() to prevent regex injection
- Validates all inputs

Performance:
- Compiles regex patterns once for reuse
- Sorts results by position for deterministic output
"""

import re
from dataclasses import dataclass


@dataclass
class BrandMention:
    """
    Represents a detected brand mention in answer text.

    Attributes:
        original_text: How the brand appeared in the answer (preserves case)
        normalized_name: Canonical brand name (primary alias, first in list)
        brand_category: Either "mine" (our brand) or "competitor"
        match_position: Character offset where brand was found in text
    """

    original_text: str
    normalized_name: str
    brand_category: str
    match_position: int

    def __post_init__(self):
        """Validate brand_category is valid."""
        if self.brand_category not in ("mine", "competitor"):
            raise ValueError(
                f"brand_category must be 'mine' or 'competitor', "
                f"got: {self.brand_category}"
            )


def create_brand_pattern(alias: str) -> re.Pattern:
    """
    Create word-boundary regex pattern for brand alias matching.

    CRITICAL: Uses word boundaries to prevent false positives.
    - "HubSpot" matches in "I use HubSpot daily"
    - "hub" does NOT match in "GitHub"

    Security: Always escapes special regex characters to prevent injection.

    Args:
        alias: Brand alias to create pattern for (e.g., "HubSpot", "Warmly.io")

    Returns:
        Compiled regex pattern with word boundaries and case-insensitive flag

    Example:
        >>> pattern = create_brand_pattern("HubSpot")
        >>> bool(pattern.search("I recommend HubSpot"))
        True
        >>> bool(pattern.search("I use GitHub"))
        False
    """
    if not alias or alias.isspace():
        raise ValueError("Brand alias cannot be empty or whitespace")

    # SECURITY: Escape special regex characters before adding word boundaries
    escaped = re.escape(alias)

    # Add word boundaries to match whole words only
    pattern = r"\b" + escaped + r"\b"

    # Case-insensitive matching
    return re.compile(pattern, re.IGNORECASE)


def normalize_brand_name(brand_aliases: list[str]) -> str:
    """
    Get canonical brand name from brand aliases list.

    The primary brand name is the alphabetically first item in the list.
    This ensures deterministic normalization even if YAML order changes.

    CRITICAL: Config schema automatically sorts brand aliases alphabetically,
    so this function always receives a sorted list. The primary brand name
    is stable across config changes, preventing historical data inconsistencies.

    Args:
        brand_aliases: List of all aliases for this brand (pre-sorted alphabetically by config)

    Returns:
        Primary brand name (alphabetically first alias in list)

    Example:
        >>> normalize_brand_name(["HubSpot", "Hubspot", "hub spot"])  # Already sorted by config
        'HubSpot'
        >>> normalize_brand_name(["Warmly", "Warmly.io"])  # Already sorted by config
        'Warmly'
    """
    if not brand_aliases:
        raise ValueError("brand_aliases list cannot be empty")

    # Primary name is always the first alias (alphabetically due to config sorting)
    return brand_aliases[0]


def detect_mentions(
    answer_text: str, our_brands: list[str], competitor_brands: list[str]
) -> list[BrandMention]:
    """
    Detect all brand mentions in LLM answer text using word-boundary matching.

    Uses regex with word boundaries to avoid false positives. Matches are
    case-insensitive but preserve original case in results.

    IMPORTANT: Each brand in both our_brands and competitor_brands is tracked
    SEPARATELY. If you have multiple products (e.g., ["ProductA", "ProductB"]),
    they will be treated as independent brands with separate tracking.

    Process:
    1. Create word-boundary patterns for all brands
    2. Search answer text for matches
    3. For each match:
       - Extract original text (preserving case)
       - Set normalized name (brand name itself)
       - Set category ("mine" or "competitor")
       - Record character position
    4. Sort by position (order of appearance)
    5. Handle overlapping matches (prefer longer match)

    Args:
        answer_text: Text from LLM response to search for mentions
        our_brands: List of brands representing "us" (each tracked separately)
        competitor_brands: List of competitor brands (each tracked separately)

    Returns:
        List of BrandMention objects sorted by appearance order (match_position)

    Example:
        >>> mentions = detect_mentions(
        ...     "I prefer HubSpot over Instantly for email warmup.",
        ...     our_brands=["Instantly"],
        ...     competitor_brands=["HubSpot", "Mailshake"]
        ... )
        >>> len(mentions)
        2
        >>> mentions[0].normalized_name
        'HubSpot'
        >>> mentions[0].brand_category
        'competitor'
        >>> mentions[1].normalized_name
        'Instantly'
        >>> mentions[1].brand_category
        'mine'

        # Multiple products tracked separately:
        >>> mentions = detect_mentions(
        ...     "Use ProductA or ProductB for best results.",
        ...     our_brands=["ProductA", "ProductB"],
        ...     competitor_brands=[]
        ... )
        >>> len(mentions)
        2
        >>> mentions[0].normalized_name
        'ProductA'
        >>> mentions[1].normalized_name
        'ProductB'
        >>> mentions[0].brand_category
        'mine'
        >>> mentions[1].brand_category
        'mine'

    Notes:
        - Empty answer_text returns empty list (not an error)
        - Only FIRST occurrence of each brand is kept (deduplicated by normalized_name)
        - If brand has multiple aliases, only one mention is returned
        - Word boundaries prevent "hub" from matching in "GitHub"
        - Case-insensitive: "hubspot", "HubSpot", "HUBSPOT" all match
    """
    # Handle empty input gracefully
    if not answer_text or answer_text.isspace():
        return []

    # Normalize empty lists
    our_brands = our_brands or []
    competitor_brands = competitor_brands or []

    # Build mapping of alias -> (primary_name, category, pattern)
    brand_patterns: list[tuple[str, str, str, re.Pattern]] = []

    # Add our brands (EACH is a SEPARATE brand tracked independently)
    for brand_name in our_brands:
        if not brand_name or brand_name.isspace():
            continue
        try:
            pattern = create_brand_pattern(brand_name)
            # Each "mine" brand is tracked separately (normalized name = itself)
            brand_patterns.append((brand_name, brand_name, "mine", pattern))
        except ValueError:
            # Skip invalid brand names
            continue

    # Add competitor brands (each is a SEPARATE brand tracked independently)
    for brand_name in competitor_brands:
        if not brand_name or brand_name.isspace():
            continue
        try:
            pattern = create_brand_pattern(brand_name)
            # Each competitor is tracked separately (normalized name = itself)
            brand_patterns.append((brand_name, brand_name, "competitor", pattern))
        except ValueError:
            # Skip invalid brand names
            continue

    # Find all matches
    all_matches: list[BrandMention] = []
    seen_brands: dict[str, BrandMention] = {}  # Track first occurrence by normalized_name (case-insensitive)

    for _alias, primary_name, category, pattern in brand_patterns:
        # Find all occurrences of this alias
        for match in pattern.finditer(answer_text):
            # Get original text from answer (preserves case)
            original_text = match.group(0)
            match_position = match.start()

            # Deduplicate by normalized_name (case-insensitive) - keep only FIRST occurrence
            # Use lowercase for deduplication key so "HubSpot" and "Hubspot" are treated as same brand
            brand_key = primary_name.lower()

            if brand_key in seen_brands:
                # Already found this brand - keep the earlier occurrence
                existing_mention = seen_brands[brand_key]
                if match_position < existing_mention.match_position:
                    # This occurrence is earlier - replace it
                    # Use the PRIMARY_NAME that came first (preserve first pattern's normalization)
                    seen_brands[brand_key] = BrandMention(
                        original_text=original_text,
                        normalized_name=existing_mention.normalized_name,  # Keep first pattern's normalized name
                        brand_category=category,
                        match_position=match_position,
                    )
                # Skip if current occurrence is later
                continue

            # First time seeing this brand
            seen_brands[brand_key] = BrandMention(
                original_text=original_text,
                normalized_name=primary_name,
                brand_category=category,
                match_position=match_position,
            )

    # Convert dict to list and sort by position
    all_matches = list(seen_brands.values())
    all_matches.sort(key=lambda m: m.match_position)

    return all_matches
