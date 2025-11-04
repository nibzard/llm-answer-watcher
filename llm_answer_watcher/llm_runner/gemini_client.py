"""
Google Gemini API client implementation for LLM Answer Watcher.

Provides synchronous HTTP client for Google Gemini API with
automatic retry logic, exponential backoff, and comprehensive error handling.

Key features:
- Retry on transient failures (429, 5xx) with exponential backoff
- Fail fast on permanent errors (401, 400, 404)
- Automatic cost estimation based on token usage
- UTC timestamp tracking
- Configurable system message per model
- Security: NEVER logs API keys

Example:
    >>> from llm_runner.gemini_client import GeminiClient
    >>> client = GeminiClient("gemini-2.0-flash-exp", api_key="...",
    ...     system_prompt="You are a helpful assistant.")
    >>> response = client.generate_answer("What are the best CRM tools?")
    >>> print(f"Answer: {response.answer_text[:100]}...")
    >>> print(f"Cost: ${response.cost_usd:.6f}")
"""

import logging
from typing import Any

import httpx

from llm_answer_watcher.llm_runner.models import LLMResponse
from llm_answer_watcher.llm_runner.retry_config import (
    NO_RETRY_STATUS_CODES,
    REQUEST_TIMEOUT,
    create_retry_decorator,
)
from llm_answer_watcher.utils.cost import estimate_cost
from llm_answer_watcher.utils.time import utc_timestamp

# Suppress HTTPX request logging to prevent test interference
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

# Google Gemini API base URL
# API endpoint format: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Maximum prompt length to prevent excessive API costs
# ~25k tokens at 4 chars/token average - prevents runaway costs from extremely long prompts
MAX_PROMPT_LENGTH = 100_000

# Get logger for this module
logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Google Gemini API client with retry logic and cost tracking.

    Implements the LLMClient protocol for Google's Gemini API with automatic retry
    on transient failures, exponential backoff, and integrated cost estimation.

    Attributes:
        model_name: Gemini model identifier (e.g., "gemini-2.0-flash-exp", "gemini-1.5-pro")
        api_key: Google API key for authentication (NEVER logged)
        system_prompt: System message sent with every request for context/instructions

    Example:
        >>> client = GeminiClient("gemini-2.0-flash-exp", "AIza...", "You are a helpful assistant.")
        >>> response = client.generate_answer("What are the best email warmup tools?")
        >>> response.tokens_used
        450
        >>> response.cost_usd
        0.000135

    Security:
        - API keys are NEVER logged in any form (not even partial)
        - API keys are only used in query parameters or headers
        - No API keys are persisted to disk or included in error messages

    Retry behavior:
        - Retries on: 429 (rate limit), 500, 502, 503, 504 (server errors)
        - Fails immediately on: 401 (auth), 400 (bad request), 404 (not found)
        - Max attempts: 3 (from retry_config.MAX_ATTEMPTS)
        - Backoff: Exponential starting at 1s, max 60s (from retry_config)
        - Timeout: 30s per request (from retry_config.REQUEST_TIMEOUT)

    Note:
        This implementation is synchronous (no async) per v1 requirements.
        Streaming is not supported in v1.
    """

    def __init__(
        self,
        model_name: str,
        api_key: str,
        system_prompt: str,
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ):
        """
        Initialize Gemini client with model, API key, system prompt, and optional tools.

        Args:
            model_name: Gemini model identifier (e.g., "gemini-2.0-flash-exp")
            api_key: Google API key for authentication
            system_prompt: System message for context/instructions
            tools: Optional list of tool configurations (not currently supported)
            tool_choice: Tool selection mode (not currently supported)

        Raises:
            ValueError: If model_name, api_key, or system_prompt is empty

        Example:
            >>> client = GeminiClient("gemini-2.0-flash-exp", "AIza...", "You are a helpful assistant.")
            >>> client.model_name
            'gemini-2.0-flash-exp'

        Security:
            - The api_key parameter is NEVER logged
            - API key validation happens server-side
            - We only validate it's non-empty locally

        Note:
            Tools are not currently supported for Gemini client in v1.
            The parameters are accepted for API compatibility but will log a warning if used.
        """
        # Validate inputs (never log api_key)
        if not model_name or model_name.isspace():
            raise ValueError("model_name cannot be empty")

        if not api_key or api_key.isspace():
            raise ValueError("api_key cannot be empty")

        if not system_prompt or system_prompt.isspace():
            raise ValueError("system_prompt cannot be empty")

        self.model_name = model_name
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_choice = tool_choice

        # Log warning if tools are provided (not yet supported)
        if tools:
            logger.warning(
                f"Tools are not currently supported for Gemini client. "
                f"Tools parameter will be ignored for model: {model_name}"
            )

        # Log initialization (never log api_key)
        logger.info(f"Initialized Gemini client for model: {model_name}")

    @create_retry_decorator()
    def generate_answer(self, prompt: str) -> LLMResponse:
        """
        Execute LLM query with automatic retry and cost tracking.

        Sends prompt to Google Gemini API with system message for
        unbiased analysis. Handles transient failures with exponential backoff
        and calculates costs based on token usage.

        Args:
            prompt: User intent prompt to send to the LLM

        Returns:
            LLMResponse: Structured response with answer text, tokens, cost, metadata

        Raises:
            ValueError: If prompt is empty
            RuntimeError: On permanent failures (auth errors, invalid requests)
                or after all retry attempts exhausted
            httpx.HTTPStatusError: On HTTP errors after retries exhausted
            httpx.ConnectError: On connection failures after retries exhausted
            httpx.TimeoutException: On timeout after retries exhausted

        Example:
            >>> client = GeminiClient("gemini-2.0-flash-exp", "AIza-...")
            >>> response = client.generate_answer("What are the best CRM tools?")
            >>> print(response.answer_text[:100])
            "Based on market research, here are the top CRM tools..."
            >>> response.provider
            'google'
            >>> response.model_name
            'gemini-2.0-flash-exp'

        Retry behavior:
            - Retries automatically on 429, 500, 502, 503, 504
            - Fails immediately on 401, 400, 404
            - Uses exponential backoff: 2s, 4s, 8s, ... up to 60s
            - Max 3 attempts total

        Security:
            - API key is sent in query parameter only
            - API key is NEVER logged, even in error messages
            - Only model name and status codes are logged

        Note:
            The @retry decorator automatically handles retries.
            If a non-retryable error occurs (e.g., 401), it checks the status
            code and raises immediately without retry.
        """
        # Validate prompt is not empty
        if not prompt or prompt.isspace():
            raise ValueError("Prompt cannot be empty")

        # Validate prompt length to prevent excessive API costs
        if len(prompt) > MAX_PROMPT_LENGTH:
            raise ValueError(
                f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH:,} characters "
                f"(received {len(prompt):,} characters). "
                f"Please shorten your prompt to stay within the limit."
            )

        # Build request payload
        # Gemini API uses 'contents' array with role/parts objects
        # System instruction is a separate parameter
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": self.system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.7,  # Default temperature for consistency
            },
        }

        # Build API endpoint URL
        # Format: /v1beta/models/{model}:generateContent?key={api_key}
        api_url = f"{GEMINI_API_BASE_URL}/models/{self.model_name}:generateContent"

        # Build headers (NEVER log api_key)
        headers = {
            "Content-Type": "application/json",
        }

        # API key is passed as query parameter for Gemini API
        params = {
            "key": self.api_key,
        }

        # Log request (NEVER log api_key or params)
        logger.debug(f"Sending request to Gemini: model={self.model_name}")

        # Make HTTP request with context manager for proper cleanup
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                response = client.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    params=params,
                )

                # Check for non-retryable errors first
                # These should fail immediately without retry
                if response.status_code in NO_RETRY_STATUS_CODES:
                    error_detail = self._extract_error_detail(response)
                    raise RuntimeError(
                        f"Gemini API error (non-retryable): "
                        f"status={response.status_code}, "
                        f"model={self.model_name}, "
                        f"detail={error_detail}"
                    )

                # Raise for retryable errors (429, 5xx)
                # The @retry decorator will catch these and retry
                response.raise_for_status()

        except httpx.HTTPStatusError as e:
            # Log error (NEVER log api_key)
            error_detail = self._extract_error_detail(e.response)
            logger.error(
                f"Gemini API HTTP error: "
                f"status={e.response.status_code}, "
                f"model={self.model_name}, "
                f"detail={error_detail}"
            )
            raise

        except httpx.ConnectError as e:
            # Connection failed (network issue)
            logger.error(
                f"Gemini API connection error: model={self.model_name}, error={e}"
            )
            raise

        except httpx.TimeoutException as e:
            # Request timed out
            logger.error(f"Gemini API timeout: model={self.model_name}, error={e}")
            raise

        # Parse response JSON
        try:
            data = response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to parse Gemini response JSON: {e}") from e

        # Extract answer text
        answer_text = self._extract_answer_text(data)

        # Extract token usage
        tokens_used, prompt_tokens, completion_tokens = self._extract_token_usage(data)

        # Calculate cost
        usage_meta = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        cost_usd = estimate_cost("google", self.model_name, usage_meta)

        # Get current timestamp
        timestamp = utc_timestamp()

        # Build and return response
        return LLMResponse(
            answer_text=answer_text,
            tokens_used=tokens_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            provider="google",
            model_name=self.model_name,
            timestamp_utc=timestamp,
            web_search_results=None,  # Web search not supported in v1
            web_search_count=0,
        )

    def _extract_answer_text(self, data: dict[str, Any]) -> str:
        """
        Extract answer text from Gemini API response.

        Args:
            data: Parsed JSON response from Gemini API

        Returns:
            str: The assistant's message content

        Raises:
            RuntimeError: If response structure is invalid or missing required fields
        """
        try:
            # Gemini API uses 'candidates' array
            candidates = data.get("candidates")
            if not candidates or not isinstance(candidates, list) or len(candidates) == 0:
                raise RuntimeError("Gemini response missing 'candidates' array")

            # Get first candidate
            candidate = candidates[0]
            if not isinstance(candidate, dict):
                raise RuntimeError("Invalid candidate structure")

            # Check for safety ratings that blocked content
            finish_reason = candidate.get("finishReason")
            if finish_reason and finish_reason != "STOP":
                # Content was blocked or had other issues
                if finish_reason in ("SAFETY", "RECITATION", "PROHIBITED_CONTENT"):
                    raise RuntimeError(
                        f"Gemini API blocked content: finishReason={finish_reason}"
                    )

            # Extract content from candidate
            content = candidate.get("content")
            if not content or not isinstance(content, dict):
                raise RuntimeError("Candidate missing 'content' field")

            # Extract parts array
            parts = content.get("parts")
            if not parts or not isinstance(parts, list) or len(parts) == 0:
                raise RuntimeError("Content missing 'parts' array")

            # Extract text from first part
            first_part = parts[0]
            if not isinstance(first_part, dict):
                raise RuntimeError("Invalid part structure")

            text = first_part.get("text")
            if text is None:
                raise RuntimeError("Part missing 'text' field")

            return str(text)

        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Invalid Gemini response structure: {e}") from e

    def _extract_token_usage(self, data: dict[str, Any]) -> tuple[int, int, int]:
        """
        Extract token usage breakdown from Gemini API response.

        Args:
            data: Parsed JSON response from Gemini API

        Returns:
            tuple[int, int, int]: (total_tokens, prompt_tokens, candidates_tokens)
                All values default to 0 if unavailable

        Note:
            Returns (0, 0, 0) if usage data is missing (graceful degradation).
            Logs warning if usage data is unavailable.
        """
        usage = data.get("usageMetadata")
        if not usage or not isinstance(usage, dict):
            logger.warning(
                f"Gemini response missing 'usageMetadata' for model={self.model_name}. "
                "Token count and cost will be zero."
            )
            return 0, 0, 0

        # Gemini uses 'promptTokenCount' and 'candidatesTokenCount'
        prompt_tokens = usage.get("promptTokenCount", 0)
        candidates_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", prompt_tokens + candidates_tokens)

        return (
            int(total_tokens) if total_tokens else 0,
            int(prompt_tokens) if prompt_tokens else 0,
            int(candidates_tokens) if candidates_tokens else 0,
        )

    def _extract_error_detail(self, response: httpx.Response) -> str:
        """
        Extract error detail from Gemini API error response.

        Args:
            response: HTTP response object from failed request

        Returns:
            str: Error message from API or generic message if unavailable

        Note:
            NEVER includes API keys in error messages.
            Only extracts error messages from response body.
        """
        try:
            error_data = response.json()
            error = error_data.get("error", {})
            message = error.get("message", "Unknown error")
            return str(message)
        except Exception:
            # Failed to parse error response
            return f"HTTP {response.status_code}"
