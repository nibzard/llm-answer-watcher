"""
Steel-based Perplexity web interface runner.

This module provides a browser automation runner for Perplexity using Steel API.
It navigates to perplexity.ai, submits queries, waits for responses, and extracts
answer text along with web search sources (which are core to Perplexity's UX).

Key components:
- SteelPerplexityRunner: Perplexity browser automation implementation
- SteelPerplexityPlugin: Plugin registration for registry

Architecture:
    Extends SteelBaseRunner to inherit session management and screenshot
    functionality, while implementing Perplexity-specific navigation and extraction
    logic including source extraction (Perplexity always shows sources).

Example:
    >>> config = SteelConfig(
    ...     steel_api_key="sk-...",
    ...     target_url="https://www.perplexity.ai",
    ...     take_screenshots=True
    ... )
    >>> runner = SteelPerplexityRunner(config)
    >>> result = runner.run_intent("What are the best CRM tools?")
    >>> print(result.answer_text)
    >>> print(f"Sources: {result.web_search_count}")
"""

import logging
import time

from ..intent_runner import IntentResult
from ..plugin_registry import RunnerRegistry
from .steel_base import SteelBaseRunner, SteelConfig

logger = logging.getLogger(__name__)


class SteelPerplexityRunner(SteelBaseRunner):
    """
    Steel-based runner for Perplexity web interface.

    Implements Perplexity-specific browser automation including:
    - Navigation to perplexity.ai
    - Query submission via search input
    - Waiting for response and source loading
    - Answer text extraction
    - Web source extraction (always present in Perplexity)

    The runner uses Steel's CDP to interact with Perplexity's web interface,
    which is optimized for search-style queries with cited sources.

    Example:
        >>> config = SteelConfig(
        ...     steel_api_key="sk-...",
        ...     target_url="https://www.perplexity.ai"
        ... )
        >>> runner = SteelPerplexityRunner(config)
        >>> result = runner.run_intent("What are the best email warmup tools?")
        >>> print(f"Answer length: {len(result.answer_text)}")
        >>> print(f"Sources found: {result.web_search_count}")
    """

    @property
    def runner_name(self) -> str:
        """Return human-readable runner identifier."""
        return "steel-perplexity"

    def run_intent(self, prompt: str) -> IntentResult:
        """
        Execute intent via Perplexity web interface.

        Args:
            prompt: User intent prompt to execute

        Returns:
            IntentResult: Structured result with answer and metadata

        Example:
            >>> result = runner.run_intent("What are the best CRM tools?")
            >>> if result.success:
            ...     print(result.answer_text)
            ...     print(f"Sources: {result.web_search_count}")
            ... else:
            ...     print(f"Error: {result.error_message}")
        """
        start_time = time.time()

        try:
            # Create Steel browser session
            session = self._create_session()
            self.session_id = session["id"]

            logger.info(f"Perplexity session created: {self.session_id}")

            # Navigate to Perplexity and submit query
            self._navigate_and_submit(session, prompt)

            # Wait for response completion
            answer_text = self._extract_answer(session)

            # Extract web sources (always present in Perplexity)
            web_search_results = self._extract_web_sources(session)
            web_search_count = len(web_search_results) if web_search_results else 0

            # Take screenshot if enabled
            screenshot_path = self._take_screenshot(self.session_id, "perplexity")

            # Save HTML snapshot if enabled
            html_snapshot_path = self._save_html(self.session_id, "perplexity")

            # Estimate cost (placeholder for now)
            cost_usd = self._estimate_cost(session, start_time)

            # Import timestamp utility
            from ...utils.time import utc_timestamp

            return IntentResult(
                answer_text=answer_text,
                runner_type="browser",
                runner_name="steel-perplexity",
                provider="perplexity-web",
                model_name="perplexity-unknown",  # Can't determine model from UI
                timestamp_utc=utc_timestamp(),
                cost_usd=cost_usd,
                tokens_used=0,  # Browser-based, no token tracking
                screenshot_path=screenshot_path,
                html_snapshot_path=html_snapshot_path,
                session_id=self.session_id,
                web_search_results=web_search_results,
                web_search_count=web_search_count,
                success=True,
            )

        except Exception as e:
            logger.error(f"Perplexity runner failed: {e}", exc_info=True)

            from ...utils.time import utc_timestamp

            return IntentResult(
                answer_text="",
                runner_type="browser",
                runner_name="steel-perplexity",
                provider="perplexity-web",
                model_name="perplexity-unknown",
                timestamp_utc=utc_timestamp(),
                cost_usd=0.0,
                success=False,
                error_message=str(e),
            )

        finally:
            # Cleanup: release session if not reusing
            if self.session_id and not self.config.session_reuse:
                self._release_session(self.session_id)

    def _navigate_and_submit(self, session: dict, prompt: str) -> None:
        """
        Navigate to Perplexity and submit query.

        Uses Steel's CDP API to:
        1. Wait for page load
        2. Find search input element
        3. Type query text
        4. Submit search

        Args:
            session: Steel session data
            prompt: User intent prompt to submit

        Raises:
            httpx.HTTPError: If Steel API calls fail
            TimeoutError: If navigation/submission times out
        """
        session_id = session["id"]

        logger.debug(f"Navigating to Perplexity for session {session_id}")

        # Wait for page to load
        time.sleep(3)

        # Use Steel's scrape API to interact with page
        logger.info(f"Submitting query to Perplexity: {prompt[:50]}...")

        # TODO: Implement actual CDP commands via Steel API:
        # 1. Wait for search input: selector = 'textarea' or 'input[type="text"]'
        # 2. Type query text
        # 3. Submit (Enter key)
        # 4. Wait for search to start (page navigation or loading indicator)

        # Placeholder: Steel API interactions would go here
        # Example structure (pseudo-code):
        # self._client.post(
        #     f"{self.steel_api_url}/sessions/{session_id}/execute",
        #     json={"command": "type", "selector": "textarea", "text": prompt}
        # )

    def _extract_answer(self, session: dict) -> str:
        """
        Extract answer text from Perplexity response.

        Uses Steel's scrape API to:
        1. Wait for response completion (sources loaded)
        2. Find answer container element
        3. Extract text content

        Args:
            session: Steel session data

        Returns:
            str: Extracted answer text

        Raises:
            httpx.HTTPError: If Steel API calls fail
            TimeoutError: If response doesn't complete within timeout
        """
        session_id = session["id"]

        logger.debug(f"Waiting for Perplexity response in session {session_id}")

        # Wait for response to complete
        # Perplexity shows progress indicator while searching
        timeout = self.config.wait_for_response_timeout
        start_time = time.time()

        while time.time() - start_time < timeout:
            time.sleep(2)

            # TODO: Check if response is complete using Steel's scrape API
            # Example: Look for absence of loading indicator
            # and presence of source citations

            # For now, just wait fixed duration
            if time.time() - start_time > 15:
                break

        # Extract answer text
        logger.debug("Extracting answer text from Perplexity")

        # TODO: Implement actual extraction via Steel's scrape API
        # Example structure (pseudo-code):
        # response = self._client.post(
        #     f"{self.steel_api_url}/sessions/{session_id}/scrape",
        #     json={"selector": ".answer-container"}
        # )
        # answer_text = response.json()["text"]

        # Placeholder: Return mock answer for now
        answer_text = (
            "[Perplexity response would be extracted here via Steel API]\n"
            f"Query submitted: {session['url']}"
        )

        logger.info(f"Extracted answer ({len(answer_text)} chars)")

        return answer_text

    def _extract_web_sources(self, session: dict) -> list[dict] | None:
        """
        Extract web sources from Perplexity response.

        Perplexity always shows source citations with URLs and titles.
        This extracts those sources for storage and analysis.

        Args:
            session: Steel session data

        Returns:
            list[dict] | None: List of sources with url/title/snippet, or None

        Note:
            This is a key differentiator for Perplexity - sources are always shown.
        """
        session_id = session["id"]

        logger.debug(f"Extracting web sources from Perplexity session {session_id}")

        # TODO: Implement source extraction via Steel's scrape API
        # Look for source citation elements (usually numbered [1], [2], etc.)
        # Extract URL, title, and optional snippet for each source
        #
        # Example structure (pseudo-code):
        # response = self._client.post(
        #     f"{self.steel_api_url}/sessions/{session_id}/scrape",
        #     json={"selector": ".source-citation"}
        # )
        # sources = response.json()["sources"]

        # Placeholder: Return empty list for now
        # In production, this would return:
        # [
        #     {"url": "https://example.com", "title": "Source Title", "snippet": "..."},
        #     ...
        # ]

        return None


@RunnerRegistry.register
class SteelPerplexityPlugin:
    """
    Plugin implementation for Steel Perplexity runner.

    Configuration:
        - steel_api_key: Steel API key
        - target_url: Perplexity URL (default: https://www.perplexity.ai)
        - session_timeout: Max session duration in seconds (default: 300)
        - wait_for_response_timeout: Max wait for response (default: 60)
        - take_screenshots: Capture screenshots (default: True)
        - save_html_snapshot: Save HTML snapshots (default: True)
        - session_reuse: Reuse sessions across intents (default: True)
        - solver: CAPTCHA solver (default: "capsolver")
        - proxy: Optional proxy config (default: None)

    Example:
        >>> config = {
        ...     "steel_api_key": "sk-...",
        ...     "target_url": "https://www.perplexity.ai",
        ...     "take_screenshots": True,
        ... }
        >>> runner = SteelPerplexityPlugin.create_runner(config)
        >>> result = runner.run_intent("What are the best CRM tools?")
    """

    @classmethod
    def plugin_name(cls) -> str:
        """Return plugin identifier."""
        return "steel-perplexity"

    @classmethod
    def runner_type(cls) -> str:
        """Return runner type."""
        return "browser"

    @classmethod
    def create_runner(cls, config: dict) -> SteelPerplexityRunner:
        """
        Create SteelPerplexityRunner from configuration.

        Args:
            config: Configuration dictionary

        Returns:
            SteelPerplexityRunner: Configured runner instance
        """
        steel_config = SteelConfig(
            steel_api_key=config["steel_api_key"],
            target_url=config.get("target_url", "https://www.perplexity.ai"),
            session_timeout=config.get("session_timeout", 300),
            wait_for_response_timeout=config.get("wait_for_response_timeout", 60),
            take_screenshots=config.get("take_screenshots", True),
            save_html_snapshot=config.get("save_html_snapshot", True),
            session_reuse=config.get("session_reuse", True),
            solver=config.get("solver", "capsolver"),
            proxy=config.get("proxy"),
            output_dir=config.get("output_dir", "./output"),
        )
        return SteelPerplexityRunner(steel_config)

    @classmethod
    def validate_config(cls, config: dict) -> tuple[bool, str]:
        """
        Validate Steel Perplexity configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if "steel_api_key" not in config:
            return False, "Missing required field: steel_api_key"

        if not config["steel_api_key"] or config["steel_api_key"].isspace():
            return False, "steel_api_key cannot be empty"

        return True, ""

    @classmethod
    def required_env_vars(cls) -> list[str]:
        """Return required environment variables."""
        return ["STEEL_API_KEY"]
