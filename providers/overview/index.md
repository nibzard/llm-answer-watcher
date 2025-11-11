# Provider Overview

LLM Answer Watcher supports 6 major LLM providers with a unified interface. Choose providers based on cost, performance, and feature requirements.

> **🌐 New in v0.2.0**: Browser Runners - Access ChatGPT and Perplexity via web UI automation to capture the true user experience. See [Browser vs API Access](#browser-vs-api-access) below.

## Supported Providers

| Provider        | Models                         | Cost Range             | Web Search  | Best For                    |
| --------------- | ------------------------------ | ---------------------- | ----------- | --------------------------- |
| **OpenAI**      | gpt-4o-mini, gpt-4o, more      | (0.15-)10/1M tokens    | ✅ Yes      | General use, cost-effective |
| **Anthropic**   | Claude 3.5 Haiku, Sonnet, Opus | (0.80-)75/1M tokens    | ❌ No       | High-quality responses      |
| **Mistral**     | mistral-large, mistral-small   | (0.30-)2/1M tokens     | ❌ No       | European alternative        |
| **X.AI (Grok)** | grok-beta, grok-2, grok-3      | (2-)25/1M tokens       | ❌ No       | X platform integration      |
| **Google**      | Gemini 2.0 Flash               | (0.075-)0.30/1M tokens | ❌ No       | Low-cost option             |
| **Perplexity**  | Sonar, Sonar Pro               | (1-)15/1M tokens       | ✅ Built-in | Grounded responses          |

## Quick Configuration

### Single Provider

```yaml
run_settings:
  models:
    - provider: "openai"
      model_name: "gpt-4o-mini"
      env_api_key: "OPENAI_API_KEY"
```

### Multiple Providers

```yaml
run_settings:
  models:
    - provider: "openai"
      model_name: "gpt-4o-mini"
      env_api_key: "OPENAI_API_KEY"

    - provider: "anthropic"
      model_name: "claude-3-5-haiku-20241022"
      env_api_key: "ANTHROPIC_API_KEY"

    - provider: "perplexity"
      model_name: "sonar-pro"
      env_api_key: "PERPLEXITY_API_KEY"
```

## Provider Selection Guide

### By Budget

**Ultra Low Cost (\<$0.005 per query):**

- Google Gemini 2.0 Flash
- OpenAI gpt-4o-mini

**Low Cost ($0.005-0.01 per query):**

- Mistral mistral-small
- Anthropic Claude 3.5 Haiku

**Medium Cost ($0.01-0.05 per query):**

- OpenAI gpt-4o
- Anthropic Claude 3.5 Sonnet
- Perplexity Sonar Pro

**High Cost (>$0.05 per query):**

- Anthropic Claude 3.5 Opus
- Grok grok-3
- OpenAI gpt-4-turbo

### By Feature

**Web Search Required:**

- ✅ OpenAI (with tools configuration)
- ✅ Perplexity (built-in)

**No Web Search:**

- Anthropic, Mistral, Grok, Google

**Grounded Responses:**

- ✅ Perplexity (best)
- ✅ OpenAI with web search

**High Quality:**

- Anthropic Claude 3.5 Sonnet/Opus
- OpenAI gpt-4o
- Perplexity Sonar Pro

**Fast Response:**

- OpenAI gpt-4o-mini
- Google Gemini Flash
- Mistral mistral-small

### By Use Case

**Cost-Optimized Monitoring:**

```yaml
models:
  - provider: "openai"
    model_name: "gpt-4o-mini"
```

**High-Quality Analysis:**

```yaml
models:
  - provider: "anthropic"
    model_name: "claude-3-5-sonnet-20241022"
```

**Multi-Provider Comparison:**

```yaml
models:
  - provider: "openai"
    model_name: "gpt-4o-mini"
  - provider: "anthropic"
    model_name: "claude-3-5-haiku-20241022"
  - provider: "perplexity"
    model_name: "sonar"
```

**Web Search Required:**

```yaml
models:
  - provider: "perplexity"
    model_name: "sonar-pro"
```

## API Key Setup

### OpenAI

```bash
export OPENAI_API_KEY=sk-your-openai-key-here
```

Get key: https://platform.openai.com/api-keys

### Anthropic

```bash
export ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
```

Get key: https://console.anthropic.com/

### Mistral

```bash
export MISTRAL_API_KEY=your-mistral-key-here
```

Get key: https://console.mistral.ai/

### X.AI (Grok)

```bash
export XAI_API_KEY=xai-your-grok-key-here
```

Get key: https://console.x.ai/

### Google Gemini

```bash
export GOOGLE_API_KEY=AIza-your-google-api-key-here
```

Get key: https://aistudio.google.com/apikey

### Perplexity

```bash
export PERPLEXITY_API_KEY=pplx-your-perplexity-key-here
```

Get key: https://www.perplexity.ai/settings/api

## Provider Comparison

### Response Quality

**Best to Good:**

1. Anthropic Claude 3.5 Opus
1. Anthropic Claude 3.5 Sonnet
1. OpenAI gpt-4o
1. Perplexity Sonar Pro
1. Mistral mistral-large
1. Grok grok-3
1. Anthropic Claude 3.5 Haiku
1. OpenAI gpt-4o-mini
1. Google Gemini 2.0 Flash
1. Mistral mistral-small

### Cost Efficiency

**Best value (quality per dollar):**

1. OpenAI gpt-4o-mini
1. Google Gemini 2.0 Flash
1. Anthropic Claude 3.5 Haiku
1. Mistral mistral-small
1. Perplexity Sonar

### Speed

**Fastest to Slowest:**

1. Google Gemini Flash
1. OpenAI gpt-4o-mini
1. Mistral models
1. Perplexity Sonar
1. Anthropic Haiku
1. OpenAI gpt-4o
1. Anthropic Sonnet
1. Grok models
1. Anthropic Opus

## Rate Limits

Default rate limits (check provider docs for current limits):

| Provider   | Requests/Min | Tokens/Min |
| ---------- | ------------ | ---------- |
| OpenAI     | 500          | 90,000     |
| Anthropic  | 50           | 100,000    |
| Mistral    | 5-60         | Varies     |
| X.AI       | 60           | 120,000    |
| Google     | 15           | 32,000     |
| Perplexity | 20           | Varies     |

**Recommendation:** Add delays between queries if hitting rate limits:

```yaml
run_settings:
  delay_between_queries: 2  # seconds
```

## Provider-Specific Features

### OpenAI

- ✅ Web search via tools
- ✅ Function calling
- ✅ JSON mode
- ✅ Vision support (not used)

See [OpenAI Provider](../openai/)

### Anthropic

- ✅ Extended context (200K tokens)
- ✅ Function calling
- ✅ JSON mode
- ✅ Thinking mode (not used)

See [Anthropic Provider](../anthropic/)

### Mistral

- ✅ European data residency
- ✅ Function calling
- ✅ JSON mode
- ✅ Competitive pricing

See [Mistral Provider](../mistral/)

### X.AI (Grok)

- ✅ X platform integration
- ✅ OpenAI-compatible API
- ✅ Real-time information
- ⚠️ Limited model selection

See [Grok Provider](../grok/)

### Google

- ✅ Very low cost
- ✅ Fast responses
- ✅ Long context (1M tokens)
- ⚠️ Newer platform

See [Google Provider](../google/)

### Perplexity

- ✅ Built-in web search
- ✅ Grounded responses
- ✅ Citations included
- ✅ Real-time information
- ⚠️ Request fees (not in cost estimate)

See [Perplexity Provider](../perplexity/)

## Multi-Provider Strategies

### Strategy 1: Cost vs Quality

Cheap model for volume, expensive for quality:

```yaml
models:
  # High volume, low cost
  - provider: "openai"
    model_name: "gpt-4o-mini"

  # Occasional high-quality check
  - provider: "anthropic"
    model_name: "claude-3-5-sonnet-20241022"
    enabled_for: ["critical-intent"]
```

### Strategy 2: Provider Diversity

Avoid single-provider dependency:

```yaml
models:
  - provider: "openai"
    model_name: "gpt-4o-mini"

  - provider: "anthropic"
    model_name: "claude-3-5-haiku-20241022"

  - provider: "google"
    model_name: "gemini-2.0-flash-exp"
```

### Strategy 3: Web Search + Standard

```yaml
models:
  # Standard queries
  - provider: "openai"
    model_name: "gpt-4o-mini"

  # Web-search enabled
  - provider: "perplexity"
    model_name: "sonar-pro"
```

## Common Issues

### API Key Errors

```text
❌ API key not found: OPENAI_API_KEY
```

**Solution:**

```bash
export OPENAI_API_KEY=sk-your-key-here
```

### Rate Limit Exceeded

```text
⚠️ Rate limit exceeded for openai/gpt-4o-mini
```

**Solutions:**

1. Add delay: `delay_between_queries: 2`
1. Reduce concurrent requests
1. Upgrade API tier

### Model Not Found

```text
❌ Model not found: gpt-4-mini
```

**Solution:** Use correct model name: `gpt-4o-mini`

See provider docs for valid models.

### Authentication Failed

```text
❌ Authentication failed: Invalid API key
```

**Solutions:**

1. Check key spelling
1. Regenerate key at provider console
1. Verify key has correct permissions

## Browser vs API Access

### Two Ways to Access Providers

Starting in v0.2.0, LLM Answer Watcher supports **two access methods** for supported providers:

| Access Method             | Providers           | How It Works                       | Use Cases                                         |
| ------------------------- | ------------------- | ---------------------------------- | ------------------------------------------------- |
| **API Access**            | All 6 providers     | Direct API calls with your API key | Production monitoring, cost-optimized, fast       |
| **Browser Access (BETA)** | ChatGPT, Perplexity | Headless browser via Steel API     | True user experience, screenshots, web UI testing |

### Key Differences

**API Access:**

- ✅ Faster (no browser overhead)
- ✅ Accurate cost tracking
- ✅ Token usage metrics
- ✅ Programmatic control
- ❌ May differ from web UI behavior
- ❌ No visual evidence

**Browser Access:**

- ✅ Captures actual user experience
- ✅ Screenshots and HTML snapshots
- ✅ Tests web UI behavior
- ✅ Free tier usage (no API costs)
- ❌ Slower (10-30s overhead)
- ❌ No cost tracking yet (shows $0.00)
- ❌ Subject to UI changes

### When to Use Each

**Use API Access when:**

- You need fast, automated monitoring
- Cost tracking is important
- You're running high-volume queries
- You need programmatic control

**Use Browser Access when:**

- You want to verify web UI behavior
- You need visual evidence (screenshots)
- You're testing free tier experience
- You want to see what actual users see

### Example: Comparing Both

```yaml
runners:
  # API access for production monitoring
  - runner_plugin: "api"
    config:
      provider: "openai"
      model_name: "gpt-4o-mini"
      api_key: "${OPENAI_API_KEY}"

  # Browser access to verify web UI
  - runner_plugin: "steel-chatgpt"
    config:
      steel_api_key: "${STEEL_API_KEY}"
      take_screenshots: true
```

This configuration runs the same query through both methods, letting you compare:

- Does the API response match what users see in ChatGPT?
- Are citations/sources displayed differently?
- Does the web UI recommend different brands?

See [Browser Runners Guide](../../BROWSER_RUNNERS/) for complete details.

## Next Steps

- **OpenAI**

  ______________________________________________________________________

  Complete OpenAI provider guide

  [OpenAI Provider →](../openai/)

- **Anthropic**

  ______________________________________________________________________

  Claude models documentation

  [Anthropic Provider →](../anthropic/)

- **Perplexity**

  ______________________________________________________________________

  Grounded LLMs with web search

  [Perplexity Provider →](../perplexity/)

- **Browser Runners**

  ______________________________________________________________________

  Web UI automation guide

  [Browser Runners →](../../BROWSER_RUNNERS/)
