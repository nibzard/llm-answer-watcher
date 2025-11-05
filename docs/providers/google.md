# Google Gemini Provider

Integration with Google's Gemini models.

## Supported Models

- `gemini-2.0-flash-exp` - Latest experimental
- `gemini-1.5-pro`
- `gemini-1.5-flash`

## Configuration

```yaml
models:
  - provider: "google"
    model_name: "gemini-2.0-flash-exp"
    env_api_key: "GOOGLE_API_KEY"
```

## Getting API Key

1. Visit [aistudio.google.com](https://aistudio.google.com/app/apikey)
2. Create API key
3. Export: `export GOOGLE_API_KEY=AIza-your-key`

See [Providers Overview](overview.md) for comparison.
