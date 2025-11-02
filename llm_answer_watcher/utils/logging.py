"""
Structured JSON logging for LLM Answer Watcher.

Provides standardized logging with:
- JSON formatted output to stderr
- UTC timestamps with timezone info
- Structured context fields
- Secret redaction (never log API keys in full)
- Component-based logger creation

All logs use Python's standard logging module with custom formatting.
Log level defaults to INFO, use setup_logging(verbose=True) for DEBUG.

Examples:
    >>> from utils.logging import setup_logging, get_logger
    >>> setup_logging(verbose=True)
    >>> logger = get_logger("config.loader")
    >>> logger.info("Config loaded", extra={"context": {"intents": 5}})

Security:
    - NEVER log full API keys
    - Redact sensitive data before logging
    - Only stderr is used (stdout reserved for user output)
"""

import json
import logging
import re
import sys
from typing import Any

from llm_answer_watcher.utils.time import utc_timestamp


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON with structured fields.

    Each log record is formatted as a JSON object with:
    - timestamp: ISO 8601 UTC timestamp
    - level: Log level (INFO, WARNING, ERROR, DEBUG)
    - component: Module/component name (from logger name)
    - message: Human-readable log message
    - context: Additional structured data (from 'context' in extra)
    - run_id: Current run identifier (from 'run_id' in extra, if available)
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: LogRecord instance from Python logging

        Returns:
            JSON string representing the log entry
        """
        # Build base log entry
        log_entry = {
            "timestamp": utc_timestamp(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }

        # Add context if provided via extra={'context': {...}}
        if hasattr(record, "context") and isinstance(record.context, dict):
            log_entry["context"] = record.context

        # Add run_id if provided via extra={'run_id': '...'}
        if hasattr(record, "run_id"):
            log_entry["run_id"] = record.run_id

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class SecretRedactingFilter(logging.Filter):
    """
    Logging filter that redacts potential secrets from log messages.

    Prevents accidental logging of:
    - API keys (OpenAI sk-*, Anthropic, etc.)
    - Authorization headers
    - Bearer tokens
    - Any string matching common secret patterns

    Replaces full secrets with redacted versions showing only last 4 chars:
    "sk-proj-abcdef123456" -> "sk-...3456"
    "Bearer abc123xyz789" -> "Bearer ***xyz789"
    """

    # Pattern to match common API key formats
    # OpenAI: sk-proj-..., sk-...
    # Anthropic: sk-ant-api03-...
    # Generic bearer tokens
    SECRET_PATTERNS = [
        (re.compile(r"\bsk-[a-zA-Z0-9_-]{20,}\b"), "sk-...{last4}"),
        (re.compile(r"\bBearer\s+[a-zA-Z0-9_-]{20,}\b"), "Bearer ***{last4}"),
        (
            re.compile(r"\b[a-zA-Z0-9_-]{32,}\b"),
            "***{last4}",
        ),  # Generic long tokens
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Redact secrets from log record message and args.

        Args:
            record: LogRecord to filter

        Returns:
            True (always allow record, but with redacted content)
        """
        # Redact message
        record.msg = self._redact_secrets(str(record.msg))

        # Redact args if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._redact_secrets(str(v)) for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._redact_secrets(str(arg)) for arg in record.args
                )

        # Redact context if present
        if hasattr(record, "context") and isinstance(record.context, dict):
            record.context = self._redact_dict(record.context)

        return True

    def _redact_secrets(self, text: str) -> str:
        """
        Redact secrets in text, keeping only last 4 characters.

        Args:
            text: Input string potentially containing secrets

        Returns:
            String with secrets replaced by redacted versions
        """
        for pattern, template in self.SECRET_PATTERNS:

            def redact_match(match: re.Match) -> str:
                matched = match.group(0)
                last4 = matched[-4:]
                return template.format(last4=last4)

            text = pattern.sub(redact_match, text)

        return text

    def _redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively redact secrets in dictionary values.

        Args:
            data: Dictionary potentially containing secrets

        Returns:
            Dictionary with secrets redacted in all string values
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._redact_secrets(value)
            elif isinstance(value, dict):
                result[key] = self._redact_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._redact_secrets(v) if isinstance(v, str) else v for v in value
                ]
            else:
                result[key] = value
        return result


def setup_logging(verbose: bool = False) -> None:
    """
    Configure structured JSON logging for the application.

    Sets up:
    - JSON formatter for structured output
    - Secret redaction filter
    - stderr output (stdout reserved for user-facing content)
    - Log level: DEBUG if verbose=True, INFO otherwise

    Args:
        verbose: If True, set log level to DEBUG. Otherwise, use INFO.

    Example:
        >>> setup_logging(verbose=True)
        >>> logger = get_logger("my.component")
        >>> logger.debug("Debug message")  # Will appear in logs
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Set level based on verbose flag
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Remove any existing handlers (prevents duplicate logs)
    root_logger.handlers.clear()

    # Create stderr handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Add JSON formatter
    formatter = JSONFormatter()
    handler.setFormatter(formatter)

    # Add secret redacting filter
    handler.addFilter(SecretRedactingFilter())

    # Add handler to root logger
    root_logger.addHandler(handler)


def get_logger(component: str) -> logging.Logger:
    """
    Get a logger instance for a specific component.

    Creates a logger with the given component name. All loggers share
    the configuration set by setup_logging().

    Args:
        component: Component name (e.g., "config.loader", "llm_runner.openai")

    Returns:
        Logger instance configured for JSON output

    Example:
        >>> logger = get_logger("config.loader")
        >>> logger.info("Loaded config file", extra={"context": {"path": "/path/to/config.yaml"}})
        # Outputs JSON: {"timestamp": "...", "level": "INFO", "component": "config.loader", ...}
    """
    return logging.getLogger(component)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    context: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> None:
    """
    Log a message with structured context and optional run_id.

    Convenience function for logging with context dict and run_id.
    Equivalent to logger.log(level, message, extra={'context': {...}, 'run_id': '...'})

    Args:
        logger: Logger instance (from get_logger)
        level: Log level (logging.INFO, logging.WARNING, etc.)
        message: Human-readable log message
        context: Optional dict with additional structured data
        run_id: Optional run identifier to include in log

    Example:
        >>> logger = get_logger("llm_runner.openai")
        >>> log_with_context(
        ...     logger,
        ...     logging.INFO,
        ...     "LLM request completed",
        ...     context={"model": "gpt-4o-mini", "tokens": 150},
        ...     run_id="2025-11-02T08-30-00Z"
        ... )
    """
    extra = {}

    if context is not None:
        extra["context"] = context

    if run_id is not None:
        extra["run_id"] = run_id

    logger.log(level, message, extra=extra if extra else None)
