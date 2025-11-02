"""
OpenAI API client implementation for LLM Answer Watcher.

Provides synchronous HTTP client for OpenAI Chat Completions API with
automatic retry logic, exponential backoff, and comprehensive error handling.

Key features:
- Retry on transient failures (429, 5xx) with exponential backoff
- Fail fast on permanent errors (401, 400, 404)
- Automatic cost estimation based on token usage
- UTC timestamp tracking
- System message injection for unbiased analysis
- Security: NEVER logs API keys

Example:
    >>> from llm_runner.openai_client import OpenAIClient
    >>> client = OpenAIClient("gpt-4o-mini", api_key="sk-...")
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

# System message to ensure unbiased, factual responses
SYSTEM_MESSAGE = (
    "You are an unbiased market analyst. Provide factual, balanced recommendations."
)

# Suppress HTTPX request logging to prevent test interference
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

# OpenAI API endpoint
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Get logger for this module
logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    OpenAI Chat Completions API client with retry logic and cost tracking.

    Implements the LLMClient protocol for OpenAI's API with automatic retry
    on transient failures, exponential backoff, and integrated cost estimation.

    Attributes:
        model_name: OpenAI model identifier (e.g., "gpt-4o-mini", "gpt-4o")
        api_key: OpenAI API key for authentication (NEVER logged)

    Example:
        >>> client = OpenAIClient("gpt-4o-mini", "sk-...")
        >>> response = client.generate_answer("What are the best email warmup tools?")
        >>> response.tokens_used
        450
        >>> response.cost_usd
        0.000135

    Security:
        - API keys are NEVER logged in any form (not even partial)
        - API keys are only used in Authorization headers
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

    def __init__(self, model_name: str, api_key: str):
        """
        Initialize OpenAI client with model and API key.

        Args:
            model_name: OpenAI model identifier (e.g., "gpt-4o-mini")
            api_key: OpenAI API key for authentication

        Raises:
            ValueError: If model_name or api_key is empty

        Example:
            >>> client = OpenAIClient("gpt-4o-mini", "sk-...")
            >>> client.model_name
            'gpt-4o-mini'

        Security:
            - The api_key parameter is NEVER logged
            - API key validation happens server-side
            - We only validate it's non-empty locally
        """
        # Validate inputs (never log api_key)
        if not model_name or model_name.isspace():
            raise ValueError("model_name cannot be empty")

        if not api_key or api_key.isspace():
            raise ValueError("api_key cannot be empty")

        self.model_name = model_name
        self.api_key = api_key

        # Log initialization (never log api_key)
        logger.info(f"Initialized OpenAI client for model: {model_name}")

    @create_retry_decorator()
    def generate_answer(self, prompt: str) -> LLMResponse:
        """
        Execute LLM query with automatic retry and cost tracking.

        Sends prompt to OpenAI Chat Completions API with system message for
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
            >>> client = OpenAIClient("gpt-4o-mini", "sk-...")
            >>> response = client.generate_answer("What are the best CRM tools?")
            >>> print(response.answer_text[:100])
            "Based on market research, here are the top CRM tools..."
            >>> response.provider
            'openai'
            >>> response.model_name
            'gpt-4o-mini'

        Retry behavior:
            - Retries automatically on 429, 500, 502, 503, 504
            - Fails immediately on 401, 400, 404
            - Uses exponential backoff: 2s, 4s, 8s, ... up to 60s
            - Max 3 attempts total

        Security:
            - API key is sent in Authorization header only
            - API key is NEVER logged, even in error messages
            - Only model name and status codes are logged

        Note:
            The @retry decorator automatically handles retries.
            If a non-retryable error occurs (e.g., 401), it checks the status
            code and raises immediately without retry.
        """
        # Validate prompt
        if not prompt or prompt.isspace():
            raise ValueError("Prompt cannot be empty")

        # Build request payload
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }

        # Build headers (NEVER log api_key)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Log request (NEVER log api_key or headers)
        logger.debug(f"Sending request to OpenAI: model={self.model_name}")

        # Make HTTP request with context manager for proper cleanup
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                response = client.post(
                    OPENAI_API_URL,
                    json=payload,
                    headers=headers,
                )

                # Check for non-retryable errors first
                # These should fail immediately without retry
                if response.status_code in NO_RETRY_STATUS_CODES:
                    error_detail = self._extract_error_detail(response)
                    raise RuntimeError(
                        f"OpenAI API error (non-retryable): "
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
                f"OpenAI API HTTP error: "
                f"status={e.response.status_code}, "
                f"model={self.model_name}, "
                f"detail={error_detail}"
            )
            raise

        except httpx.ConnectError as e:
            # Connection failed (network issue)
            logger.error(
                f"OpenAI API connection error: model={self.model_name}, error={e}"
            )
            raise

        except httpx.TimeoutException as e:
            # Request timed out
            logger.error(f"OpenAI API timeout: model={self.model_name}, error={e}")
            raise

        # Parse response JSON
        try:
            data = response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to parse OpenAI response JSON: {e}") from e

        # Extract answer text
        answer_text = self._extract_answer_text(data)

        # Extract token usage
        tokens_used = self._extract_token_usage(data)

        # Calculate cost
        usage_meta = data.get("usage", {})
        cost_usd = estimate_cost("openai", self.model_name, usage_meta)

        # Get current timestamp
        timestamp = utc_timestamp()

        # Build and return response
        return LLMResponse(
            answer_text=answer_text,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            provider="openai",
            model_name=self.model_name,
            timestamp_utc=timestamp,
        )

    def _extract_answer_text(self, data: dict[str, Any]) -> str:
        """
        Extract answer text from OpenAI API response.

        Args:
            data: Parsed JSON response from OpenAI API

        Returns:
            str: The assistant's message content

        Raises:
            RuntimeError: If response structure is invalid or missing required fields
        """
        try:
            choices = data.get("choices")
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                raise RuntimeError("OpenAI response missing 'choices' array")

            message = choices[0].get("message")
            if not message or not isinstance(message, dict):
                raise RuntimeError("OpenAI response missing 'message' object")

            content = message.get("content")
            if content is None:
                raise RuntimeError("OpenAI response missing 'content' field")

            # Content can be empty string (valid), but not None
            return str(content)

        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Invalid OpenAI response structure: {e}") from e

    def _extract_token_usage(self, data: dict[str, Any]) -> int:
        """
        Extract total token usage from OpenAI API response.

        Args:
            data: Parsed JSON response from OpenAI API

        Returns:
            int: Total tokens used (prompt + completion), or 0 if unavailable

        Note:
            Returns 0 if usage data is missing (graceful degradation).
            Logs warning if usage data is unavailable.
        """
        usage = data.get("usage")
        if not usage or not isinstance(usage, dict):
            logger.warning(
                f"OpenAI response missing 'usage' data for model={self.model_name}. "
                "Token count and cost will be zero."
            )
            return 0

        total_tokens = usage.get("total_tokens", 0)
        return int(total_tokens) if total_tokens else 0

    def _extract_error_detail(self, response: httpx.Response) -> str:
        """
        Extract error detail from OpenAI API error response.

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
