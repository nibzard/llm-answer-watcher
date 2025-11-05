# Budget-Constrained Monitoring

Minimize costs while maintaining monitoring quality.

## Cost-Optimized Configuration

```yaml
run_settings:
  output_dir: "./output"

  models:
    # Use cheapest effective model
    - provider: "openai"
      model_name: "gpt-4o-mini"
      env_api_key: "OPENAI_API_KEY"

  # Regex extraction (no extra LLM calls)
  use_llm_rank_extraction: false

  # Set budget limits
  budget:
    enabled: true
    max_per_run_usd: 0.10
    max_per_intent_usd: 0.02

brands:
  mine: ["YourBrand"]
  # Focus on top 3 competitors only
  competitors: ["TopCompetitor1", "TopCompetitor2", "TopCompetitor3"]

intents:
  # Single most valuable intent
  - id: "main-query"
    prompt: "What are the best tools?"
```

## Estimated Costs

- 1 intent × 1 model: ~$0.002 per run
- 3 intents × 1 model: ~$0.006 per run
- Run daily for a month: ~$0.18/month

See [Cost Management](../user-guide/features/cost-management.md).
