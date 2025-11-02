"""
Tests for llm_runner.openai_client module.

Tests cover:
- OpenAIClient initialization and validation
- Successful API calls with proper response parsing
- Retry logic on transient failures (429, 5xx)
- Immediate failure on non-retryable errors (401, 400, 404)
- Token usage extraction and cost calculation
- Error handling and logging (without logging API keys)
- Edge cases (empty responses, malformed JSON, missing fields)
"""

import logging

import httpx
import pytest
from freezegun import freeze_time

from llm_answer_watcher.llm_runner.models import LLMResponse
from llm_answer_watcher.llm_runner.openai_client import (
    OPENAI_API_URL,
    SYSTEM_MESSAGE,
    OpenAIClient,
)


class TestOpenAIClientInit:
    """Test suite for OpenAIClient initialization."""

    def test_init_success(self):
        """Test successful client initialization."""
        client = OpenAIClient("gpt-4o-mini", "sk-test123")

        assert client.model_name == "gpt-4o-mini"
        assert client.api_key == "sk-test123"

    def test_init_different_model(self):
        """Test initialization with different model."""
        client = OpenAIClient("gpt-4o", "sk-prod456")

        assert client.model_name == "gpt-4o"
        assert client.api_key == "sk-prod456"

    def test_init_empty_model_name(self):
        """Test that empty model_name raises ValueError."""
        with pytest.raises(ValueError, match="model_name cannot be empty"):
            OpenAIClient("", "sk-test123")

    def test_init_whitespace_model_name(self):
        """Test that whitespace-only model_name raises ValueError."""
        with pytest.raises(ValueError, match="model_name cannot be empty"):
            OpenAIClient("   ", "sk-test123")

    def test_init_empty_api_key(self):
        """Test that empty api_key raises ValueError."""
        with pytest.raises(ValueError, match="api_key cannot be empty"):
            OpenAIClient("gpt-4o-mini", "")

    def test_init_whitespace_api_key(self):
        """Test that whitespace-only api_key raises ValueError."""
        with pytest.raises(ValueError, match="api_key cannot be empty"):
            OpenAIClient("gpt-4o-mini", "   ")

    def test_init_logs_model_not_api_key(self, caplog):
        """Test that initialization logs model name but NEVER logs API key."""
        caplog.set_level(logging.INFO)

        OpenAIClient("gpt-4o-mini", "sk-secret123")

        # Should log model name
        assert "gpt-4o-mini" in caplog.text

        # Should NEVER log API key
        assert "sk-secret123" not in caplog.text
        assert "secret" not in caplog.text


class TestGenerateAnswerSuccess:
    """Test suite for successful OpenAI API calls."""

    @freeze_time("2025-11-02T08:30:45Z")
    def test_generate_answer_success(self, httpx_mock):
        """Test successful API call with complete response."""
        # Mock successful OpenAI API response
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Based on market research, the top CRM tools are Salesforce, HubSpot, and Zoho.",
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
                "model": "gpt-4o-mini",
            },
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")
        response = client.generate_answer("What are the best CRM tools?")

        # Verify response structure
        assert isinstance(response, LLMResponse)
        assert (
            response.answer_text
            == "Based on market research, the top CRM tools are Salesforce, HubSpot, and Zoho."
        )
        assert response.tokens_used == 150
        assert response.cost_usd > 0  # Should have calculated cost
        assert response.provider == "openai"
        assert response.model_name == "gpt-4o-mini"
        assert response.timestamp_utc == "2025-11-02T08:30:45Z"

    def test_generate_answer_sends_correct_payload(self, httpx_mock):
        """Test that API request includes system message and correct structure."""
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            json={
                "choices": [{"message": {"content": "Test response"}}],
                "usage": {"total_tokens": 100},
            },
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")
        client.generate_answer("Test prompt")

        # Verify request was made
        request = httpx_mock.get_request()
        assert request is not None

        # Verify request structure
        payload = request.read()
        import json

        data = json.loads(payload)

        assert data["model"] == "gpt-4o-mini"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "system"
        assert data["messages"][0]["content"] == SYSTEM_MESSAGE
        assert data["messages"][1]["role"] == "user"
        assert data["messages"][1]["content"] == "Test prompt"
        assert data["temperature"] == 0.7

    def test_generate_answer_sends_auth_header(self, httpx_mock):
        """Test that API request includes Bearer token in Authorization header."""
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            json={
                "choices": [{"message": {"content": "Test"}}],
                "usage": {"total_tokens": 10},
            },
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")
        client.generate_answer("Test")

        # Verify Authorization header
        request = httpx_mock.get_request()
        assert request.headers["Authorization"] == "Bearer sk-test123"
        assert request.headers["Content-Type"] == "application/json"

    def test_generate_answer_empty_content(self, httpx_mock):
        """Test handling of empty content in response (valid but unusual)."""
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            json={
                "choices": [{"message": {"content": ""}}],
                "usage": {"total_tokens": 10},
            },
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")
        response = client.generate_answer("Test")

        assert response.answer_text == ""
        assert response.tokens_used == 10

    def test_generate_answer_large_response(self, httpx_mock):
        """Test handling of large response with high token count."""
        large_content = "A" * 10000
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            json={
                "choices": [{"message": {"content": large_content}}],
                "usage": {"total_tokens": 50000},
            },
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")
        response = client.generate_answer("Generate large text")

        assert response.answer_text == large_content
        assert response.tokens_used == 50000


class TestGenerateAnswerValidation:
    """Test suite for input validation."""

    def test_generate_answer_empty_prompt(self, httpx_mock):
        """Test that empty prompt raises ValueError."""
        client = OpenAIClient("gpt-4o-mini", "sk-test123")

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            client.generate_answer("")

    def test_generate_answer_whitespace_prompt(self, httpx_mock):
        """Test that whitespace-only prompt raises ValueError."""
        client = OpenAIClient("gpt-4o-mini", "sk-test123")

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            client.generate_answer("   \n\t  ")


class TestGenerateAnswerNonRetryableErrors:
    """Test suite for non-retryable errors (401, 400, 404)."""

    def test_generate_answer_401_unauthorized(self, httpx_mock):
        """Test that 401 error raises RuntimeError immediately (no retry)."""
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=401,
            json={"error": {"message": "Invalid API key"}},
        )

        client = OpenAIClient("gpt-4o-mini", "sk-invalid")

        with pytest.raises(RuntimeError, match="non-retryable"):
            client.generate_answer("Test")

        # Verify only one request was made (no retry)
        assert len(httpx_mock.get_requests()) == 1

    def test_generate_answer_400_bad_request(self, httpx_mock):
        """Test that 400 error raises RuntimeError immediately (no retry)."""
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=400,
            json={"error": {"message": "Invalid request format"}},
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")

        with pytest.raises(RuntimeError, match="non-retryable"):
            client.generate_answer("Test")

    def test_generate_answer_404_not_found(self, httpx_mock):
        """Test that 404 error raises RuntimeError immediately (no retry)."""
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=404,
            json={"error": {"message": "Endpoint not found"}},
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")

        with pytest.raises(RuntimeError, match="non-retryable"):
            client.generate_answer("Test")


class TestGenerateAnswerRetryableErrors:
    """Test suite for retryable errors (429, 5xx) with retry logic."""

    def test_generate_answer_429_rate_limit_then_success(self, httpx_mock):
        """Test that 429 error is retried and succeeds on second attempt."""
        # First call: rate limit
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=429,
            json={"error": {"message": "Rate limit exceeded"}},
        )

        # Second call: success
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=200,
            json={
                "choices": [{"message": {"content": "Success after retry"}}],
                "usage": {"total_tokens": 50},
            },
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")
        response = client.generate_answer("Test")

        assert response.answer_text == "Success after retry"
        assert len(httpx_mock.get_requests()) == 2  # Two attempts

    def test_generate_answer_500_server_error_then_success(self, httpx_mock):
        """Test that 500 error is retried and succeeds."""
        # First call: server error
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=500,
            json={"error": {"message": "Internal server error"}},
        )

        # Second call: success
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=200,
            json={
                "choices": [{"message": {"content": "Recovered"}}],
                "usage": {"total_tokens": 30},
            },
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")
        response = client.generate_answer("Test")

        assert response.answer_text == "Recovered"

    def test_generate_answer_502_bad_gateway_exhausts_retries(self, httpx_mock):
        """Test that 502 exhausts retries and raises error."""
        # Mock 3 failed attempts (max retries from retry_config)
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=502,
            json={"error": {"message": "Bad gateway"}},
        )
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=502,
            json={"error": {"message": "Bad gateway"}},
        )
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=502,
            json={"error": {"message": "Bad gateway"}},
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")

        with pytest.raises(httpx.HTTPStatusError):
            client.generate_answer("Test")


class TestGenerateAnswerResponseParsing:
    """Test suite for response parsing edge cases."""

    def test_generate_answer_missing_choices(self, httpx_mock):
        """Test that missing 'choices' raises RuntimeError."""
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            json={"usage": {"total_tokens": 10}},  # Missing 'choices'
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")

        with pytest.raises(RuntimeError, match="missing 'choices' array"):
            client.generate_answer("Test")

    def test_generate_answer_empty_choices(self, httpx_mock):
        """Test that empty choices array raises RuntimeError."""
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            json={"choices": [], "usage": {"total_tokens": 10}},
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")

        with pytest.raises(RuntimeError, match="missing 'choices' array"):
            client.generate_answer("Test")

    def test_generate_answer_missing_message(self, httpx_mock):
        """Test that missing 'message' raises RuntimeError."""
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            json={"choices": [{}], "usage": {"total_tokens": 10}},
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")

        with pytest.raises(RuntimeError, match="missing 'message' object"):
            client.generate_answer("Test")

    def test_generate_answer_missing_content(self, httpx_mock):
        """Test that missing 'content' raises RuntimeError."""
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            json={
                "choices": [{"message": {"role": "assistant"}}],  # No 'content'
                "usage": {"total_tokens": 10},
            },
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")

        with pytest.raises(RuntimeError, match="missing 'content' field"):
            client.generate_answer("Test")

    def test_generate_answer_missing_usage(self, httpx_mock, caplog):
        """Test that missing usage data returns 0 tokens with warning."""
        caplog.set_level(logging.WARNING)

        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            json={"choices": [{"message": {"content": "Test"}}]},  # No 'usage'
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")
        response = client.generate_answer("Test")

        assert response.tokens_used == 0
        assert response.cost_usd == 0.0
        assert "missing 'usage' data" in caplog.text

    def test_generate_answer_invalid_json(self, httpx_mock):
        """Test that invalid JSON raises RuntimeError."""
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            content=b"Not valid JSON",
        )

        client = OpenAIClient("gpt-4o-mini", "sk-test123")

        with pytest.raises(RuntimeError, match="Failed to parse OpenAI response JSON"):
            client.generate_answer("Test")


class TestGenerateAnswerLogging:
    """Test suite for logging behavior (security-critical)."""

    def test_generate_answer_never_logs_api_key(self, httpx_mock, caplog):
        """Test that API key is NEVER logged in any form."""
        caplog.set_level(logging.DEBUG)

        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            json={
                "choices": [{"message": {"content": "Test"}}],
                "usage": {"total_tokens": 10},
            },
        )

        client = OpenAIClient("gpt-4o-mini", "sk-secret123")
        client.generate_answer("Test prompt")

        # Should log model name
        assert "gpt-4o-mini" in caplog.text

        # Should NEVER log API key (not even partial)
        assert "sk-secret123" not in caplog.text
        assert "secret" not in caplog.text
        assert "Bearer" not in caplog.text  # Don't log auth header

    def test_generate_answer_error_never_logs_api_key(self, httpx_mock, caplog):
        """Test that errors NEVER log API key."""
        caplog.set_level(logging.DEBUG)

        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=500,
            json={"error": {"message": "Internal server error"}},
        )
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=500,
            json={"error": {"message": "Internal server error"}},
        )
        httpx_mock.add_response(
            method="POST",
            url=OPENAI_API_URL,
            status_code=500,
            json={"error": {"message": "Internal server error"}},
        )

        client = OpenAIClient("gpt-4o-mini", "sk-secret123")

        with pytest.raises(httpx.HTTPStatusError):
            client.generate_answer("Test")

        # Should log error
        assert "500" in caplog.text or "error" in caplog.text.lower()

        # Should NEVER log API key
        assert "sk-secret123" not in caplog.text
        assert "secret" not in caplog.text


class TestExtractErrorDetail:
    """Test suite for error detail extraction."""

    def test_extract_error_detail_valid_json(self):
        """Test extracting error message from valid error response."""
        client = OpenAIClient("gpt-4o-mini", "sk-test")

        response = httpx.Response(
            status_code=401,
            json={"error": {"message": "Invalid API key"}},
        )

        detail = client._extract_error_detail(response)
        assert detail == "Invalid API key"

    def test_extract_error_detail_missing_message(self):
        """Test fallback when error message is missing."""
        client = OpenAIClient("gpt-4o-mini", "sk-test")

        response = httpx.Response(
            status_code=500,
            json={"error": {}},
        )

        detail = client._extract_error_detail(response)
        assert detail == "Unknown error"

    def test_extract_error_detail_invalid_json(self):
        """Test fallback when JSON parsing fails."""
        client = OpenAIClient("gpt-4o-mini", "sk-test")

        response = httpx.Response(
            status_code=500,
            content=b"Not JSON",
        )

        detail = client._extract_error_detail(response)
        assert detail == "HTTP 500"
