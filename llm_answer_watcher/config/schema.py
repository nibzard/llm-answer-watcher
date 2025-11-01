"""
Configuration schema models for LLM Answer Watcher.

This module defines Pydantic models for validating and parsing the
watcher.config.yaml file. All models use Python 3.12+ type hints and
Pydantic v2 field validators for comprehensive validation.

Models:
    ModelConfig: LLM model configuration (provider, model_name, env_api_key)
    RunSettings: Runtime settings (output paths, models, feature flags)
    Brands: Brand alias collections (mine vs competitors)
    Intent: Buyer-intent query configuration
    WatcherConfig: Root configuration model (validates entire YAML)
    RuntimeModel: Resolved model configuration with API key
    RuntimeConfig: Runtime configuration with resolved API keys
"""

from typing import Literal

from pydantic import BaseModel, field_validator


class ModelConfig(BaseModel):
    """
    LLM model configuration from watcher.config.yaml.

    Specifies which LLM to call and where to find its API key in the environment.

    Attributes:
        provider: LLM provider name (openai, anthropic, mistral)
        model_name: Specific model identifier (e.g., "gpt-4o-mini")
        env_api_key: Environment variable name containing the API key
    """

    provider: Literal["openai", "anthropic", "mistral"]
    model_name: str
    env_api_key: str

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model_name is non-empty."""
        if not v or v.isspace():
            raise ValueError("model_name cannot be empty")
        return v

    @field_validator("env_api_key")
    @classmethod
    def validate_env_api_key(cls, v: str) -> str:
        """Validate env_api_key is non-empty."""
        if not v or v.isspace():
            raise ValueError("env_api_key cannot be empty")
        return v


class RunSettings(BaseModel):
    """
    Runtime settings for watcher execution.

    Defines output locations, which models to use, and feature flags.

    Attributes:
        output_dir: Directory for run artifacts (JSON files, HTML reports)
        sqlite_db_path: Path to SQLite database for historical tracking
        models: List of LLM models to query for each intent
        use_llm_rank_extraction: Enable LLM-assisted ranking (slower, more accurate)
    """

    output_dir: str
    sqlite_db_path: str
    models: list[ModelConfig]
    use_llm_rank_extraction: bool = False

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, v: str) -> str:
        """Validate output_dir is non-empty."""
        if not v or v.isspace():
            raise ValueError("output_dir cannot be empty")
        return v

    @field_validator("sqlite_db_path")
    @classmethod
    def validate_sqlite_db_path(cls, v: str) -> str:
        """Validate sqlite_db_path is non-empty."""
        if not v or v.isspace():
            raise ValueError("sqlite_db_path cannot be empty")
        return v

    @field_validator("models")
    @classmethod
    def validate_models(cls, v: list[ModelConfig]) -> list[ModelConfig]:
        """Validate at least one model is configured."""
        if not v:
            raise ValueError("At least one model must be configured")
        return v


class Brands(BaseModel):
    """
    Brand alias collections for mention detection.

    Defines which brand names represent "us" vs competitors for tracking
    in LLM responses.

    Attributes:
        mine: List of aliases representing our brand (required, min 1)
        competitors: List of competitor brand aliases (optional)
    """

    mine: list[str]
    competitors: list[str] = []

    @field_validator("mine")
    @classmethod
    def validate_mine(cls, v: list[str]) -> list[str]:
        """
        Validate 'mine' brand aliases.

        Removes empty/whitespace-only entries and ensures at least one
        valid alias remains.
        """
        # Remove empty/whitespace-only entries
        cleaned = [b.strip() for b in v if b and not b.isspace()]
        if not cleaned:
            raise ValueError("At least one brand alias required in 'mine'")
        return cleaned

    @field_validator("competitors")
    @classmethod
    def validate_competitors(cls, v: list[str]) -> list[str]:
        """
        Validate competitor brand aliases.

        Removes empty/whitespace-only entries. Empty competitor list is allowed.
        """
        # Remove empty/whitespace-only entries
        cleaned = [b.strip() for b in v if b and not b.isspace()]
        return cleaned


class Intent(BaseModel):
    """
    Buyer-intent query configuration.

    Represents a question we repeatedly ask LLMs to monitor brand mentions
    and rankings.

    Attributes:
        id: Unique identifier slug (alphanumeric, hyphens, underscores)
        prompt: The actual question to ask the LLM
    """

    id: str
    prompt: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """
        Validate intent ID is a valid slug.

        Must be non-empty and contain only alphanumeric characters,
        hyphens, and underscores.
        """
        if not v or v.isspace():
            raise ValueError("Intent ID cannot be empty")
        # Check for valid slug format (alphanumeric, hyphens, underscores)
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError(
                f"Intent ID must be alphanumeric with hyphens/underscores: {v}"
            )
        return v

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt is non-empty."""
        if not v or v.isspace():
            raise ValueError("Intent prompt cannot be empty")
        return v


class WatcherConfig(BaseModel):
    """
    Root configuration model for watcher.config.yaml.

    Validates the entire configuration file structure and enforces
    business rules like unique intent IDs.

    Attributes:
        run_settings: Runtime settings (output paths, models, feature flags)
        brands: Brand alias collections (mine vs competitors)
        intents: List of buyer-intent queries to monitor
    """

    run_settings: RunSettings
    brands: Brands
    intents: list[Intent]

    @field_validator("intents")
    @classmethod
    def validate_intents_unique(cls, v: list[Intent]) -> list[Intent]:
        """
        Validate intents list is non-empty and all IDs are unique.

        Raises:
            ValueError: If no intents configured or duplicate IDs found
        """
        if not v:
            raise ValueError("At least one intent must be configured")

        # Check for duplicate IDs
        ids = [intent.id for intent in v]
        if len(ids) != len(set(ids)):
            duplicates = {id for id in ids if ids.count(id) > 1}
            raise ValueError(f"Duplicate intent IDs found: {duplicates}")

        return v


class RuntimeModel(BaseModel):
    """
    Resolved model configuration with API key.

    Created at runtime after loading API keys from environment variables.
    This is what the LLM runner uses to make API calls.

    Attributes:
        provider: LLM provider name (openai, anthropic, mistral)
        model_name: Specific model identifier
        api_key: Resolved API key from environment (NEVER log this)
    """

    provider: str
    model_name: str
    api_key: str

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is non-empty."""
        if not v or v.isspace():
            raise ValueError("provider cannot be empty")
        return v

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model_name is non-empty."""
        if not v or v.isspace():
            raise ValueError("model_name cannot be empty")
        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key is non-empty."""
        if not v or v.isspace():
            raise ValueError("API key cannot be empty")
        return v


class RuntimeConfig(BaseModel):
    """
    Runtime configuration with resolved API keys.

    Created by config.loader after validating YAML and resolving
    environment variables. This is the contract passed to the runner.

    Attributes:
        run_settings: Runtime settings from config
        brands: Brand aliases from config
        intents: Intent queries from config
        models: Resolved model configurations with API keys
    """

    run_settings: RunSettings
    brands: Brands
    intents: list[Intent]
    models: list[RuntimeModel]

    @field_validator("models")
    @classmethod
    def validate_models(cls, v: list[RuntimeModel]) -> list[RuntimeModel]:
        """Validate at least one model is configured."""
        if not v:
            raise ValueError("At least one model must be configured in runtime config")
        return v
