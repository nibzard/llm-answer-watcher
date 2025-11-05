"""
Configuration loader for LLM Answer Watcher.

This module loads YAML configuration files, validates them with Pydantic models,
and resolves API keys from environment variables to create a RuntimeConfig.

The loader implements a clear separation between configuration specification
(WatcherConfig from YAML) and runtime configuration (RuntimeConfig with resolved
API keys), ensuring secrets never get committed to version control.

Functions:
    load_config: Main entrypoint to load and validate watcher.config.yaml
    resolve_api_keys: Helper to resolve environment variables to API keys
"""

import os
from pathlib import Path

import yaml
from pydantic import ValidationError

from llm_answer_watcher.exceptions import (
    APIKeyMissingError,
    ConfigFileNotFoundError,
    ConfigValidationError,
)
from llm_answer_watcher.system_prompts import get_provider_default, load_prompt

from .schema import RuntimeConfig, RuntimeModel, WatcherConfig


def load_config(config_path: str | Path) -> RuntimeConfig:
    """
    Load watcher.config.yaml and resolve API keys from environment variables.

    This function:
    1. Loads YAML from the specified path
    2. Validates structure using WatcherConfig Pydantic model
    3. Resolves API key environment variables to actual secrets
    4. Returns RuntimeConfig with resolved API keys ready for LLM calls

    Args:
        config_path: Path to watcher.config.yaml file (relative or absolute)

    Returns:
        RuntimeConfig with resolved API keys and validated configuration

    Raises:
        ConfigFileNotFoundError: If config file doesn't exist at the specified path
        ConfigValidationError: If YAML is invalid or config validation fails
        APIKeyMissingError: If required API keys are missing from environment

    Example:
        >>> config = load_config("examples/watcher.config.yaml")
        >>> len(config.models)
        2
        >>> config.models[0].api_key  # Resolved from environment
        'sk-...'

    Security:
        - API keys are loaded from environment variables only
        - API keys are NEVER logged or written to disk
        - Uses yaml.safe_load() to prevent code injection
    """
    # Convert to Path object for robust path handling
    config_path = Path(config_path)

    # Check file exists before attempting to read
    if not config_path.exists():
        raise ConfigFileNotFoundError(f"Configuration file not found: {config_path}")

    # Load YAML content
    try:
        with config_path.open(encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(
            f"Invalid YAML syntax in {config_path}: {e}"
        ) from e
    except Exception as e:
        raise ConfigValidationError(
            f"Failed to read configuration file {config_path}: {e}"
        ) from e

    # Handle empty YAML file
    if raw_config is None:
        raise ConfigValidationError(f"Configuration file is empty: {config_path}")

    # Validate configuration structure with Pydantic
    try:
        watcher_config = WatcherConfig.model_validate(raw_config)
    except ValidationError as e:
        # Format validation errors in a user-friendly way
        error_messages = []
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            error_messages.append(f"  - {loc}: {msg}")

        raise ConfigValidationError(
            f"Configuration validation failed in {config_path}:\n"
            + "\n".join(error_messages)
        ) from e

    # Resolve API keys from environment variables
    try:
        resolved_models = resolve_api_keys(watcher_config)
    except APIKeyMissingError:
        # Re-raise API key errors as-is
        raise
    except ConfigValidationError:
        # Re-raise config validation errors as-is
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise ConfigValidationError(
            f"Failed to resolve API keys from {config_path}: {e}"
        ) from e

    # Build RuntimeConfig with resolved API keys
    return RuntimeConfig(
        run_settings=watcher_config.run_settings,
        brands=watcher_config.brands,
        intents=watcher_config.intents,
        models=resolved_models,
    )


def resolve_api_keys(config: WatcherConfig) -> list[RuntimeModel]:
    """
    Resolve API key environment variables and system prompts for runtime use.

    Takes the list of ModelConfig from WatcherConfig and resolves:
    1. env_api_key references to actual API keys from environment
    2. system_prompt references to actual prompt text from JSON files

    Args:
        config: Validated WatcherConfig with model configurations

    Returns:
        List of RuntimeModel instances with resolved API keys and system prompts

    Raises:
        APIKeyMissingError: If any required environment variable is not set
        ConfigValidationError: If provider is unsupported or system prompt files cannot be loaded

    Example:
        >>> # Assuming OPENAI_API_KEY is set in environment
        >>> config = WatcherConfig(...)
        >>> models = resolve_api_keys(config)
        >>> models[0].api_key  # Contains actual key from environment
        'sk-proj-...'
        >>> models[0].system_prompt  # Contains prompt text from JSON
        'You are ChatGPT...'

    Security:
        - NEVER logs API keys (not even partial values)
        - Fails fast if environment variable is missing
        - API keys are only held in memory, never persisted
    """
    # List of implemented providers (updated to include all current providers)
    IMPLEMENTED_PROVIDERS = {"openai", "anthropic", "mistral", "grok", "google"}
    PLANNED_PROVIDERS: set[str] = set()  # All planned providers are now implemented

    resolved_models: list[RuntimeModel] = []

    for model_config in config.run_settings.models:
        # Validate provider is implemented
        if model_config.provider not in IMPLEMENTED_PROVIDERS:
            if model_config.provider in PLANNED_PROVIDERS:
                raise ConfigValidationError(
                    f"Provider '{model_config.provider}' is not yet implemented. "
                    f"Currently supported providers: {', '.join(sorted(IMPLEMENTED_PROVIDERS))}. "
                    f"Planned providers: {', '.join(sorted(PLANNED_PROVIDERS))}. "
                    f"Please use an implemented provider or check back in a future release."
                )
            else:
                raise ConfigValidationError(
                    f"Unknown provider '{model_config.provider}'. "
                    f"Supported providers: {', '.join(sorted(IMPLEMENTED_PROVIDERS))}."
                )

        # Get environment variable name from config
        env_var_name = model_config.env_api_key

        # Resolve to actual API key value
        api_key = os.environ.get(env_var_name)

        # Fail fast if environment variable is not set
        if not api_key:
            raise APIKeyMissingError(
                f"Environment variable ${env_var_name} not set "
                f"(required for {model_config.provider}/{model_config.model_name}). "
                f"Please set it in your environment or .env file."
            )

        # Validate API key is not just whitespace
        if api_key.isspace():
            raise APIKeyMissingError(
                f"Environment variable ${env_var_name} is empty or whitespace "
                f"(required for {model_config.provider}/{model_config.model_name})"
            )

        # Resolve system prompt from JSON file
        try:
            if model_config.system_prompt:
                # Use specified system prompt
                prompt_obj = load_prompt(model_config.system_prompt)
            else:
                # Fall back to provider default
                prompt_obj = get_provider_default(model_config.provider)

            system_prompt_text = prompt_obj.prompt

        except Exception as e:
            raise ConfigValidationError(
                f"Failed to load system prompt for {model_config.provider}/{model_config.model_name}: {e}"
            ) from e

        # Build RuntimeModel with resolved API key, system prompt, and tools
        runtime_model = RuntimeModel(
            provider=model_config.provider,
            model_name=model_config.model_name,
            api_key=api_key,
            system_prompt=system_prompt_text,
            tools=model_config.tools,
            tool_choice=model_config.tool_choice,
        )

        resolved_models.append(runtime_model)

    return resolved_models
