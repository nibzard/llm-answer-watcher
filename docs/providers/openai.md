# OpenAI Provider

Integration with OpenAI's GPT models.

## Supported Models

- `gpt-4o` - Latest GPT-4 Optimized
- `gpt-4o-mini` - Cost-effective model (recommended)
- `gpt-4-turbo` - Fast GPT-4
- `gpt-3.5-turbo` - Legacy model

## Configuration

```yaml
models:
  - provider: "openai"
    model_name: "gpt-4o-mini"
    env_api_key: "OPENAI_API_KEY"
```

## Getting API Key

1. Visit [platform.openai.com](https://platform.openai.com/api-keys)
2. Create new secret key
3. Export: `export OPENAI_API_KEY=sk-your-key`

## Pricing

- **gpt-4o-mini**: $0.15/1M input, $0.60/1M output
- **gpt-4o**: $2.50/1M input, $10/1M output

See [Providers Overview](overview.md) for comparison.
