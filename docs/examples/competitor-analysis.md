# Competitor Analysis

Track competitors comprehensively across multiple queries.

## Example Configuration

```yaml
run_settings:
  output_dir: "./output"
  models:
    - provider: "openai"
      model_name: "gpt-4o-mini"
      env_api_key: "OPENAI_API_KEY"

brands:
  mine: ["YourBrand"]
  competitors:
    - "TopCompetitor"
    - "RisingStartup"
    - "IndustryLeader"
    - "NichePlayer"
    - "AlternativeTool"

intents:
  - id: "best-overall"
    prompt: "What are the best tools in the category?"
  - id: "for-startups"
    prompt: "Best tools for startups?"
  - id: "for-enterprise"
    prompt: "Best enterprise tools?"
  - id: "affordable-options"
    prompt: "Most affordable tools?"
```

## Analyzing Results

```sql
-- Competitor appearance frequency
SELECT brand, COUNT(*) as mentions
FROM mentions
WHERE normalized_name != 'yourbrand'
GROUP BY brand
ORDER BY mentions DESC;
```
