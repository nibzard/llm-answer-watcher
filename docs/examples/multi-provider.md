# Multi-Provider Monitoring

Compare how different LLM providers represent your brand.

## Example Configuration

```yaml
run_settings:
  output_dir: "./output"
  sqlite_db_path: "./output/watcher.db"

  models:
    - provider: "openai"
      model_name: "gpt-4o-mini"
      env_api_key: "OPENAI_API_KEY"

    - provider: "anthropic"
      model_name: "claude-3-5-haiku-20241022"
      env_api_key: "ANTHROPIC_API_KEY"

    - provider: "mistral"
      model_name: "mistral-small-latest"
      env_api_key: "MISTRAL_API_KEY"

brands:
  mine: ["YourBrand"]
  competitors: ["CompetitorA", "CompetitorB"]

intents:
  - id: "best-tools"
    prompt: "What are the best tools?"
```

## Benefits

- See which providers favor your brand
- Identify provider-specific biases
- Optimize for specific LLM platforms

See [Basic Monitoring](basic-monitoring.md) for simpler setup.
