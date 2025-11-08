"""
Base class for Steel API browser automation runners.

This module provides common functionality for all Steel-based browser runners
including session management, navigation, screenshot capture, and HTML extraction.

Key components:
- SteelConfig: Configuration dataclass for Steel API settings
- SteelBaseRunner: Base class with common Steel operations

Architecture:
    The base class handles Steel API interactions (session creation, cleanup,
    screenshot capture) while concrete implementations (ChatGPT, Perplexity)
    override site-specific methods for navigation and content extraction.

Example:
    >>> class MyChatRunner(SteelBaseRunner):
    ...     def _navigate_and_submit(self, session: dict, prompt: str):
    ...         # Site-specific navigation
    ...         pass
    ...
    ...     def _extract_answer(self, session: dict) -> str:
    ...         # Site-specific extraction
    ...         pass
    ...
    >>> config = SteelConfig(steel_api_key="sk-...", target_url="https://example.com")
    >>> runner = MyChatRunner(config)
    >>> result = runner.run_intent("What are the best CRM tools?")
"""

import base64
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from ...utils.time import utc_timestamp

logger = logging.getLogger(__name__)


@dataclass
class SteelConfig:
    """
    Configuration for Steel browser automation.

    Attributes:
        steel_api_key: Steel API key for authentication
        target_url: Starting URL for browser session
        session_timeout: Maximum session duration in seconds (default: 300)
        wait_for_response_timeout: Max wait for response in seconds (default: 60)
        take_screenshots: Whether to capture screenshots (default: True)
        save_html_snapshot: Whether to save HTML snapshots (default: True)
        session_reuse: Whether to reuse sessions (default: True)
        solver: CAPTCHA solver service (default: "capsolver")
        proxy: Optional proxy configuration (default: None)
        output_dir: Directory for saving screenshots/HTML (default: "./output")
    """

    steel_api_key: str
    target_url: str
    session_timeout: int = 300
    wait_for_response_timeout: int = 60
    take_screenshots: bool = True
    save_html_snapshot: bool = True
    session_reuse: bool = True
    solver: str = "capsolver"
    proxy: str | None = None
    output_dir: str = "./output"


class SteelBaseRunner:
    """
    Base class for Steel API browser automation runners.

    Provides common Steel API operations including:
    - Session creation and cleanup
    - Screenshot capture
    - HTML snapshot extraction
    - Error handling and retry logic

    Subclasses must implement:
    - _navigate_and_submit(): Site-specific navigation and prompt submission
    - _extract_answer(): Site-specific answer extraction
    - runner_name property: Human-readable identifier

    Attributes:
        config: Steel configuration
        steel_api_url: Steel API base URL
        session_id: Current browser session ID (if active)
        _client: HTTP client for Steel API calls

    Example:
        >>> class MyRunner(SteelBaseRunner):
        ...     @property
        ...     def runner_name(self) -> str:
        ...         return "my-steel-runner"
        ...
        ...     def _navigate_and_submit(self, session: dict, prompt: str):
        ...         # Navigate to site and submit prompt
        ...         pass
        ...
        ...     def _extract_answer(self, session: dict) -> str:
        ...         # Extract answer from page
        ...         return "Extracted answer text"
        ...
        >>> config = SteelConfig(steel_api_key="sk-...", target_url="https://example.com")
        >>> runner = MyRunner(config)
        >>> result = runner.run_intent("What are the best CRM tools?")
    """

    def __init__(self, config: SteelConfig):
        """
        Initialize Steel base runner.

        Args:
            config: Steel configuration
        """
        self.config = config
        self.steel_api_url = "https://api.steel.dev/v1"
        self.session_id: str | None = None
        self._client = httpx.Client(timeout=60.0)

    @property
    def runner_type(self) -> str:
        """Return runner type (always 'browser' for Steel runners)."""
        return "browser"

    @property
    def runner_name(self) -> str:
        """Return human-readable runner identifier (must be overridden)."""
        raise NotImplementedError("Subclasses must implement runner_name property")

    def _create_session(self) -> dict:
        """
        Create Steel browser session.

        Returns:
            dict: Session data from Steel API with keys:
                - id: Session identifier
                - url: Session viewer URL
                - status: Session status

        Raises:
            httpx.HTTPError: If session creation fails
        """
        logger.debug(f"Creating Steel session for {self.config.target_url}")

        response = self._client.post(
            f"{self.steel_api_url}/sessions",
            headers={"Steel-Api-Key": self.config.steel_api_key},
            json={
                "url": self.config.target_url,
                "timeout": self.config.session_timeout,
                "solver": self.config.solver,
                "proxy": self.config.proxy,
            },
        )
        response.raise_for_status()

        session_data = response.json()
        logger.info(f"Created Steel session: {session_data.get('id', 'unknown')}")

        return session_data

    def _release_session(self, session_id: str) -> None:
        """
        Release Steel browser session.

        Args:
            session_id: Session identifier to release

        Note:
            Errors are logged but not raised to avoid breaking cleanup logic.
        """
        try:
            logger.debug(f"Releasing Steel session: {session_id}")
            response = self._client.delete(
                f"{self.steel_api_url}/sessions/{session_id}",
                headers={"Steel-Api-Key": self.config.steel_api_key},
            )
            response.raise_for_status()
            logger.info(f"Released Steel session: {session_id}")
        except Exception as e:
            logger.warning(f"Failed to release session {session_id}: {e}")

    def _take_screenshot(self, session_id: str, intent_id: str) -> str | None:
        """
        Capture screenshot from browser session.

        Args:
            session_id: Session identifier
            intent_id: Intent identifier (for filename)

        Returns:
            str | None: Path to saved screenshot, or None if capture failed

        Note:
            Screenshot is saved as PNG in output directory.
        """
        if not self.config.take_screenshots:
            return None

        try:
            logger.debug(f"Taking screenshot for session {session_id}")

            response = self._client.get(
                f"{self.steel_api_url}/sessions/{session_id}/screenshot",
                headers={"Steel-Api-Key": self.config.steel_api_key},
            )
            response.raise_for_status()

            # Screenshot is returned as base64-encoded PNG
            screenshot_data = response.json()
            image_base64 = screenshot_data.get("image", "")

            if not image_base64:
                logger.warning("Screenshot response missing image data")
                return None

            # Decode and save
            image_bytes = base64.b64decode(image_base64)
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            screenshot_path = output_dir / f"screenshot_{intent_id}_{session_id}.png"
            screenshot_path.write_bytes(image_bytes)

            logger.info(f"Saved screenshot: {screenshot_path}")
            return str(screenshot_path)

        except Exception as e:
            logger.warning(f"Failed to capture screenshot: {e}", exc_info=True)
            return None

    def _save_html(self, session_id: str, intent_id: str) -> str | None:
        """
        Save HTML snapshot from browser session.

        Args:
            session_id: Session identifier
            intent_id: Intent identifier (for filename)

        Returns:
            str | None: Path to saved HTML file, or None if save failed
        """
        if not self.config.save_html_snapshot:
            return None

        try:
            logger.debug(f"Extracting HTML for session {session_id}")

            response = self._client.get(
                f"{self.steel_api_url}/sessions/{session_id}/html",
                headers={"Steel-Api-Key": self.config.steel_api_key},
            )
            response.raise_for_status()

            html_content = response.text
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            html_path = output_dir / f"html_{intent_id}_{session_id}.html"
            html_path.write_text(html_content, encoding="utf-8")

            logger.info(f"Saved HTML snapshot: {html_path}")
            return str(html_path)

        except Exception as e:
            logger.warning(f"Failed to save HTML snapshot: {e}", exc_info=True)
            return None

    def _navigate_and_submit(self, session: dict, prompt: str) -> None:
        """
        Navigate to target site and submit prompt.

        This is a site-specific operation that must be implemented by subclasses.

        Args:
            session: Steel session data
            prompt: User intent prompt to submit

        Raises:
            NotImplementedError: Always (must be overridden)
        """
        raise NotImplementedError("Subclasses must implement _navigate_and_submit")

    def _extract_answer(self, session: dict) -> str:
        """
        Extract answer text from page.

        This is a site-specific operation that must be implemented by subclasses.

        Args:
            session: Steel session data

        Returns:
            str: Extracted answer text

        Raises:
            NotImplementedError: Always (must be overridden)
        """
        raise NotImplementedError("Subclasses must implement _extract_answer")

    def _estimate_cost(self, session: dict, start_time: float) -> float:
        """
        Estimate cost for Steel browser session.

        Args:
            session: Steel session data
            start_time: Session start timestamp

        Returns:
            float: Estimated cost in USD (0.0 for now, can be enhanced later)

        Note:
            Currently returns 0.0. Can be enhanced to calculate actual cost
            based on session duration and Steel pricing ($0.10-0.30/hour).
        """
        # Placeholder for cost tracking
        # Steel charges per hour ($0.10-0.30/hour based on plan)
        # Can calculate: (time.time() - start_time) / 3600 * hourly_rate
        return 0.0

    def __del__(self):
        """Cleanup: close HTTP client."""
        try:
            self._client.close()
        except Exception:
            pass
