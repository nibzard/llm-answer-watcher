# Basic Monitoring Example

A complete, production-ready example for monitoring brand visibility across multiple LLM providers.

## Use Case

Monitor how LLMs recommend your email warmup tool versus competitors.

**Goals:**

- Track if your brand appears in recommendations
- See which competitors are mentioned alongside you
- Understand ranking positions
- Keep costs low (<$0.05 per run)

## Complete Configuration

Create `watcher.config.yaml`:

```yaml
run_settings:
  output_dir: "./output"
  sqlite_db_path: "./output/watcher.db"

  models:
    # Primary model - cheap and fast
    - provider: "openai"
      model_name: "gpt-4o-mini"
      env_api_key: "OPENAI_API_KEY"
      system_prompt: "openai/gpt-4-default"

    # Secondary model - different provider for comparison
    - provider: "anthropic"
      model_name: "claude-3-5-haiku-20241022"
      env_api_key: "ANTHROPIC_API_KEY"

  # Use regex extraction (free)
  use_llm_rank_extraction: false

  # Budget protection
  budget:
    enabled: true
    max_per_run_usd: 0.10  # 10 cents max
    warn_threshold_usd: 0.05  # Warn at 5 cents

brands:
  # Your brand (with variations)
  mine:
    - "Warmly"
    - "Warmly.io"
    - "Warmly AI"

  # Top competitors
  competitors:
    - "Instantly"
    - "Instantly.ai"
    - "Lemwarm"
    - "Lemlist"
    - "HubSpot"
    - "Apollo.io"
    - "Woodpecker"
    - "Mailshake"

intents:
  # Core buyer-intent queries
  - id: "best-email-warmup-tools"
    prompt: "What are the best email warmup tools?"

  - id: "email-warmup-for-cold-email"
    prompt: "Which email warmup tools are best for cold email campaigns?"

  - id: "improve-email-deliverability"
    prompt: "What tools help improve email deliverability?"

  - id: "hubspot-alternatives"
    prompt: "What are good alternatives to HubSpot for email warmup?"
```

## Environment Setup

Create `.env` file:

```bash
# API Keys
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Optional: Custom output directory
# LLM_WATCHER_OUTPUT_DIR=./custom-output
```

Load environment:

```bash
source .env
```

## Run Monitoring

### First Run

```bash
# Validate configuration
llm-answer-watcher validate --config watcher.config.yaml

# Run monitoring
llm-answer-watcher run --config watcher.config.yaml
```

**Expected Output:**

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃         🔍 LLM Answer Watcher - Run Started         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✓ Configuration loaded from watcher.config.yaml
  ├── Intents: 4
  ├── Models: 2 (OpenAI, Anthropic)
  ├── Brands: 3 monitored, 8 competitors
  └── Estimated cost: $0.0168

⠋ Querying OpenAI gpt-4o-mini: "What are the best email warmup tools?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Progress: 8/8 queries completed (100%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                  ✅ Run Complete                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

📊 Results Summary
  ├── Run ID: 2025-11-05T14-30-00Z
  ├── Queries completed: 8/8
  ├── Total cost: $0.0168 USD
  ├── Your brands found: 6 mentions across 4 intents
  └── Competitors found: 15 mentions

💰 Cost Breakdown
  ├── OpenAI gpt-4o-mini: $0.0084 (4 queries)
  └── Anthropic claude-3-5-haiku: $0.0084 (4 queries)

📂 Output Location
  ├── Directory: ./output/2025-11-05T14-30-00Z/
  ├── Database: ./output/watcher.db
  └── HTML Report: ./output/2025-11-05T14-30-00Z/report.html

🌐 Open report in browser:
  open ./output/2025-11-05T14-30-00Z/report.html
```

## View Results

### HTML Report

```bash
open ./output/2025-11-05T14-30-00Z/report.html
```

**Report includes:**

- Summary statistics
- Brand mention tables
- Rank distribution charts
- Cost breakdown
- Raw LLM responses

### JSON Results

```bash
# View run summary
cat ./output/2025-11-05T14-30-00Z/run_meta.json | jq '.'

# View specific intent results
cat ./output/2025-11-05T14-30-00Z/intent_best-email-warmup-tools_parsed_openai_gpt-4o-mini.json | jq '.'
```

### SQLite Database

```bash
sqlite3 ./output/watcher.db

# View latest run
SELECT * FROM runs ORDER BY timestamp_utc DESC LIMIT 1;

# View your brand mentions
SELECT * FROM mentions WHERE is_mine = 1 ORDER BY timestamp_utc DESC;

# Compare competitors
SELECT brand, COUNT(*) as mentions, AVG(rank_position) as avg_rank
FROM mentions
WHERE is_mine = 0 AND rank_position IS NOT NULL
GROUP BY brand
ORDER BY mentions DESC;
```

## Analyzing Results

### Check Brand Visibility

```sql
-- Did we appear in any responses?
SELECT
    intent_id,
    model_provider,
    model_name,
    brand,
    rank_position
FROM mentions
WHERE is_mine = 1
  AND run_id = '2025-11-05T14-30-00Z'
ORDER BY intent_id, rank_position;
```

**Example Output:**

```
best-email-warmup-tools | openai | gpt-4o-mini | Warmly | 2
best-email-warmup-tools | anthropic | claude-3-5-haiku | Warmly.io | 3
email-warmup-for-cold-email | openai | gpt-4o-mini | Warmly | 1
improve-email-deliverability | anthropic | claude-3-5-haiku | Warmly | 4
```

**Interpretation:**

- ✅ Appeared in 4/8 responses (50% visibility)
- 🥇 Ranked #1 once
- 📊 Average rank: 2.5

### Compare vs Competitors

```sql
-- How do we rank vs competitors?
SELECT
    brand,
    COUNT(*) as total_mentions,
    COUNT(DISTINCT intent_id) as intents_appeared,
    AVG(rank_position) as avg_rank,
    MIN(rank_position) as best_rank
FROM mentions
WHERE run_id = '2025-11-05T14-30-00Z'
  AND rank_position IS NOT NULL
GROUP BY brand
ORDER BY total_mentions DESC, avg_rank ASC;
```

**Example Output:**

```
Instantly | 7 | 4 | 1.4 | 1
Warmly | 6 | 4 | 2.5 | 1
Lemwarm | 5 | 3 | 3.2 | 2
HubSpot | 4 | 2 | 2.0 | 1
```

**Interpretation:**

- 🥈 2nd most mentioned (6 mentions)
- 📈 Average rank 2.5 (middle of pack)
- 🎯 Opportunity: Improve from #2-3 to #1

### Identify Gaps

```sql
-- Which intents didn't mention us?
SELECT intent_id
FROM (SELECT DISTINCT intent_id FROM mentions WHERE run_id = '2025-11-05T14-30-00Z')
WHERE intent_id NOT IN (
    SELECT DISTINCT intent_id
    FROM mentions
    WHERE run_id = '2025-11-05T14-30-00Z'
      AND is_mine = 1
);
```

**Example Output:**

```
hubspot-alternatives
```

**Interpretation:**

- ❌ Not mentioned in "HubSpot alternatives" query
- 🎯 Action: Optimize content for "alternative" queries

## Schedule Regular Monitoring

### Daily Cron Job

Create `/home/user/bin/run-brand-monitoring.sh`:

```bash
#!/bin/bash
set -e

PROJECT_DIR="/home/user/projects/llm-answer-watcher"
cd "$PROJECT_DIR"

# Load API keys
source .env

# Activate virtualenv
source .venv/bin/activate

# Run monitoring
llm-answer-watcher run --config watcher.config.yaml --yes --quiet >> logs/monitoring.log 2>&1

# Alert if no brand mentions
if [ $? -eq 0 ]; then
    MENTIONS=$(sqlite3 output/watcher.db "SELECT COUNT(*) FROM mentions WHERE is_mine=1 AND timestamp_utc >= datetime('now', '-1 hour')")

    if [ "$MENTIONS" -eq 0 ]; then
        echo "⚠️ WARNING: No brand mentions in latest run" | mail -s "Brand Visibility Alert" admin@example.com
    fi
fi
```

Add to crontab:

```bash
# Run daily at 9 AM
0 9 * * * /home/user/bin/run-brand-monitoring.sh
```

## Cost Analysis

### Actual Costs

```sql
-- Total cost last 30 days
SELECT SUM(total_cost_usd) as total_cost
FROM runs
WHERE timestamp_utc >= datetime('now', '-30 days');

-- Cost by provider
SELECT
    model_provider,
    SUM(estimated_cost_usd) as provider_cost,
    COUNT(*) as queries
FROM answers_raw
WHERE timestamp_utc >= datetime('now', '-30 days')
GROUP BY model_provider;
```

### Cost Optimization

**Current config costs:**

- 4 intents × 2 models = 8 queries
- ~$0.001-0.002 per query
- **Total: ~$0.016 per run**

**Monthly (daily runs):**

- 30 runs × $0.016 = **$0.48/month**

**To reduce costs:**

1. Use only 1 model:

```yaml
models:
  - provider: "openai"
    model_name: "gpt-4o-mini"  # $0.008/run
```

2. Reduce intents:

```yaml
intents:
  - id: "best-email-warmup-tools"  # Only 1 intent
    prompt: "What are the best email warmup tools?"
```

**Optimized cost:** $0.002/run = $0.06/month

## Troubleshooting

### No Brand Mentions

**Problem:** Your brand never appears

**Solutions:**

1. Check brand aliases:

```bash
# View raw responses
cat output/*/intent_*_raw_*.json | jq '.answer_text' | grep -i "warmly"
```

2. Add more aliases:

```yaml
brands:
  mine:
    - "Warmly"
    - "Warmly.io"
    - "Warmly AI"
    - "Warmly Email"  # Add this
```

3. Update intent prompts:

```yaml
# More specific prompt
- id: "warmly-vs-competitors"
  prompt: "Compare Warmly vs Instantly vs Lemwarm for email warmup"
```

### High Costs

**Problem:** Costs exceed budget

**Solutions:**

1. Enable budget warnings:

```yaml
budget:
  enabled: true
  max_per_run_usd: 0.05  # Abort if > 5 cents
```

2. Reduce models or intents
3. Switch to cheaper models

### Rate Limiting

**Problem:** API rate limits hit

**Solution:** Add delays:

```yaml
run_settings:
  delay_between_queries: 2  # 2 second delay
```

## Next Steps

<div class="grid cards" markdown>

-   :material-compare: **Multi-Provider**

    ---

    Compare multiple LLM providers

    [Multi-Provider Example →](multi-provider.md)

-   :material-chart-line: **Competitor Analysis**

    ---

    Deep dive into competitor positioning

    [Competitor Analysis →](competitor-analysis.md)

-   :material-database: **Historical Trends**

    ---

    Track changes over time

    [Trends Analysis →](../data-analytics/trends-analysis.md)

-   :material-robot: **Automation**

    ---

    Set up scheduled monitoring

    [Automation Guide →](../user-guide/usage/automation.md)

</div>
