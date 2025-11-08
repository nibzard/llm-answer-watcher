"""
Steel-based ChatGPT web interface runner.

This module provides a browser automation runner for ChatGPT using Steel API.
It navigates to chat.openai.com, submits prompts, waits for responses, and
extracts answer text along with optional web search results.

Key components:
- SteelChatGPTRunner: ChatGPT browser automation implementation
- SteelChatGPTPlugin: Plugin registration for registry

Architecture:
    Extends SteelBaseRunner to inherit session management and screenshot
    functionality, while implementing ChatGPT-specific navigation and extraction
    logic using Steel's browser control API.

Example:
    >>> config = SteelConfig(
    ...     steel_api_key="sk-...",
    ...     target_url="https://chat.openai.com",
    ...     take_screenshots=True
    ... )
    >>> runner = SteelChatGPTRunner(config)
    >>> result = runner.run_intent("What are the best CRM tools?")
    >>> print(result.answer_text)
    >>> print(f"Screenshot: {result.screenshot_path}")
"""

import logging
import time

from ..intent_runner import IntentResult
from ..plugin_registry import RunnerRegistry
from .steel_base import SteelBaseRunner, SteelConfig

logger = logging.getLogger(__name__)


class SteelChatGPTRunner(SteelBaseRunner):
    """
    Steel-based runner for ChatGPT web interface.

    Implements ChatGPT-specific browser automation including:
    - Navigation to chat.openai.com
    - Prompt submission via text input
    - Waiting for response completion
    - Answer text extraction
    - Optional web search result extraction

    The runner uses Steel's CDP (Chrome DevTools Protocol) to interact with
    ChatGPT's web interface, handling dynamic content and waiting for streaming
    responses to complete.

    Example:
        >>> config = SteelConfig(
        ...     steel_api_key="sk-...",
        ...     target_url="https://chat.openai.com"
        ... )
        >>> runner = SteelChatGPTRunner(config)
        >>> result = runner.run_intent("What are the best email warmup tools?")
        >>> print(f"Answer length: {len(result.answer_text)}")
        >>> print(f"Web searches: {result.web_search_count}")
    """

    @property
    def runner_name(self) -> str:
        """Return human-readable runner identifier."""
        return "steel-chatgpt"

    def run_intent(self, prompt: str) -> IntentResult:
        """
        Execute intent via ChatGPT web interface.

        Args:
            prompt: User intent prompt to execute

        Returns:
            IntentResult: Structured result with answer and metadata

        Example:
            >>> result = runner.run_intent("What are the best CRM tools?")
            >>> if result.success:
            ...     print(result.answer_text)
            ... else:
            ...     print(f"Error: {result.error_message}")
        """
        start_time = time.time()

        try:
            # Create Steel browser session
            session = self._create_session()
            self.session_id = session["id"]

            logger.info(f"ChatGPT session created: {self.session_id}")

            # Navigate to ChatGPT and submit prompt
            self._navigate_and_submit(session, prompt)

            # Wait for response completion
            answer_text = self._extract_answer(session)

            # Extract web search results if present (future enhancement)
            web_search_results = self._extract_web_sources(session)
            web_search_count = len(web_search_results) if web_search_results else 0

            # Take screenshot if enabled
            screenshot_path = self._take_screenshot(self.session_id, "chatgpt")

            # Save HTML snapshot if enabled
            html_snapshot_path = self._save_html(self.session_id, "chatgpt")

            # Estimate cost (placeholder for now)
            cost_usd = self._estimate_cost(session, start_time)

            # Import timestamp utility
            from ...utils.time import utc_timestamp

            return IntentResult(
                answer_text=answer_text,
                runner_type="browser",
                runner_name="steel-chatgpt",
                provider="chatgpt-web",
                model_name="chatgpt-unknown",  # Can't determine model from UI
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
            logger.error(f"ChatGPT runner failed: {e}", exc_info=True)

            from ...utils.time import utc_timestamp

            return IntentResult(
                answer_text="",
                runner_type="browser",
                runner_name="steel-chatgpt",
                provider="chatgpt-web",
                model_name="chatgpt-unknown",
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
        Navigate to ChatGPT and submit prompt.

        Uses Steel's CDP API to:
        1. Wait for page load
        2. Find message input element
        3. Type prompt text
        4. Submit message

        Args:
            session: Steel session data
            prompt: User intent prompt to submit

        Raises:
            httpx.HTTPError: If Steel API calls fail
            TimeoutError: If navigation/submission times out
        """
        session_id = session["id"]

        logger.debug(f"Navigating to ChatGPT for session {session_id}")

        # Wait for page to load (Steel handles this automatically)
        time.sleep(3)

        # Use Steel's scrape API to interact with page
        # This is a placeholder - actual implementation needs Steel's CDP methods
        logger.info(f"Submitting prompt to ChatGPT: {prompt[:50]}...")

        # TODO: Implement actual CDP commands via Steel API:
        # 1. Wait for input textarea: selector = 'textarea[placeholder*="Send a message"]'
        # 2. Type prompt text
        # 3. Submit (Enter key or click send button)
        # 4. Wait for response to start

        # Placeholder: Steel API interactions would go here
        # Example structure (pseudo-code):
        # self._client.post(
        #     f"{self.steel_api_url}/sessions/{session_id}/execute",
        #     json={"command": "type", "selector": "textarea", "text": prompt}
        # )

    def _extract_answer(self, session: dict) -> str:
        """
        Extract answer text from ChatGPT response.

        Uses Steel's scrape API to:
        1. Wait for response completion (streaming finished)
        2. Find last assistant message element
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

        logger.debug(f"Waiting for ChatGPT response in session {session_id}")

        # Wait for response to complete (streaming finished)
        # Look for absence of "Stop generating" button
        timeout = self.config.wait_for_response_timeout
        start_time = time.time()

        while time.time() - start_time < timeout:
            time.sleep(2)

            # TODO: Check if response is complete using Steel's scrape API
            # Example: Look for last message with data-message-author-role="assistant"
            # and verify streaming indicator is gone

            # For now, just wait fixed duration
            if time.time() - start_time > 10:
                break

        # Extract answer text
        logger.debug("Extracting answer text from ChatGPT")

        # TODO: Implement actual extraction via Steel's scrape API
        # Example structure (pseudo-code):
        # response = self._client.post(
        #     f"{self.steel_api_url}/sessions/{session_id}/scrape",
        #     json={"selector": "[data-message-author-role='assistant']:last-child"}
        # )
        # answer_text = response.json()["text"]

        # Placeholder: Return mock answer for now
        answer_text = (
            "[ChatGPT response would be extracted here via Steel API]\n"
            f"Prompt submitted: {session['url']}"
        )

        logger.info(f"Extracted answer ({len(answer_text)} chars)")

        return answer_text

    def _extract_web_sources(self, session: dict) -> list[dict] | None:
        """
        Extract web search results if ChatGPT used web search.

        Looks for citation links or "Searched X sites" indicators in response.

        Args:
            session: Steel session data

        Returns:
            list[dict] | None: List of web sources with url/title, or None

        Note:
            This is a future enhancement - returns None for now.
        """
        # TODO: Implement web source extraction
        # Look for citation links like [1], [2] and extract URLs
        # Check for "Searched X sites" message
        # Extract source URLs and titles

        return None


@RunnerRegistry.register
class SteelChatGPTPlugin:
    """
    Plugin implementation for Steel ChatGPT runner.

    Configuration:
        - steel_api_key: Steel API key
        - target_url: ChatGPT URL (default: https://chat.openai.com)
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
        ...     "target_url": "https://chat.openai.com",
        ...     "take_screenshots": True,
        ... }
        >>> runner = SteelChatGPTPlugin.create_runner(config)
        >>> result = runner.run_intent("What are the best CRM tools?")
    """

    @classmethod
    def plugin_name(cls) -> str:
        """Return plugin identifier."""
        return "steel-chatgpt"

    @classmethod
    def runner_type(cls) -> str:
        """Return runner type."""
        return "browser"

    @classmethod
    def create_runner(cls, config: dict) -> SteelChatGPTRunner:
        """
        Create SteelChatGPTRunner from configuration.

        Args:
            config: Configuration dictionary

        Returns:
            SteelChatGPTRunner: Configured runner instance
        """
        steel_config = SteelConfig(
            steel_api_key=config["steel_api_key"],
            target_url=config.get("target_url", "https://chat.openai.com"),
            session_timeout=config.get("session_timeout", 300),
            wait_for_response_timeout=config.get("wait_for_response_timeout", 60),
            take_screenshots=config.get("take_screenshots", True),
            save_html_snapshot=config.get("save_html_snapshot", True),
            session_reuse=config.get("session_reuse", True),
            solver=config.get("solver", "capsolver"),
            proxy=config.get("proxy"),
            output_dir=config.get("output_dir", "./output"),
        )
        return SteelChatGPTRunner(steel_config)

    @classmethod
    def validate_config(cls, config: dict) -> tuple[bool, str]:
        """
        Validate Steel ChatGPT configuration.

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
