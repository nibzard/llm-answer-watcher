# LLM Answer Watcher

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

> Monitor how Large Language Models talk about your brand versus competitors in buyer-intent queries

LLM Answer Watcher is a production-ready CLI tool that asks LLMs specific questions (e.g., "best email warmup tools"), extracts structured signals (Did we appear? Who else appeared? In what rank?), and stores results in SQLite for historical tracking.

## ✨ Key Features

- **🔍 Brand Mention Detection**: Word-boundary regex matching prevents false positives
- **📊 Historical Tracking**: SQLite database stores all responses for trend analysis
- **🤖 Multi-Provider Support**: OpenAI, Anthropic, Mistral, X.AI Grok, Google Gemini, and extensible provider system
- **📈 Rank Extraction**: Automatic detection of where brands appear in LLM responses
- **💰 Cost Estimation**: Built-in token counting and cost calculation
- **🎯 Dual-Mode CLI**: Beautiful Rich output for humans, structured JSON for AI agents
- **📋 HTML Reports**: Auto-generated reports with historical data visualizations
- **🔒 Local-First**: All data stored locally, BYOK (Bring Your Own Keys)

## 🚀 Quick Start

```bash
# Install with uv (recommended)
uv sync

# Or with pip
pip install llm-answer-watcher

# Set your API keys
export OPENAI_API_KEY=your_key_here
export ANTHROPIC_API_KEY=your_key_here
export MISTRAL_API_KEY=your_key_here
export XAI_API_KEY=your_key_here  # For Grok
export GOOGLE_API_KEY=your_key_here  # For Gemini

# Run with example config
llm-answer-watcher run --config examples/watcher.config.yaml
```

## 📋 Prerequisites

- **Python 3.12+ or 3.13** (Required)
- **uv** (recommended) or **pip** for package management
- **API keys** for LLM providers (OpenAI, Anthropic, Mistral, etc.)

### API Key Setup

Set your API keys as environment variables:

```bash
# OpenAI
export OPENAI_API_KEY=sk-your-openai-key-here

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Mistral
export MISTRAL_API_KEY=mistral-your-key-here

# X.AI Grok
export XAI_API_KEY=xai-your-grok-key-here

# Google Gemini
export GOOGLE_API_KEY=AIza-your-google-api-key-here
```

## 🔧 Installation

### Option 1: Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/nikolabalic/llm-answer-watcher.git
cd llm-answer-watcher

# Install dependencies and create virtual environment
uv sync

# Activate the virtual environment (optional, uv handles this automatically)
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Option 2: Using pip

```bash
# Clone the repository
git clone https://github.com/nikolabalic/llm-answer-watcher.git
cd llm-answer-watcher

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .
```

## ⚙️ Configuration

Create a `watcher.config.yaml` file with the following structure:

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
      model_name: "mistral-large-latest"
      env_api_key: "MISTRAL_API_KEY"

    - provider: "grok"
      model_name: "grok-beta"
      env_api_key: "XAI_API_KEY"

    - provider: "google"
      model_name: "gemini-2.0-flash-exp"
      env_api_key: "GOOGLE_API_KEY"

  use_llm_rank_extraction: false  # Use regex-based extraction (faster/cheaper)

brands:
  mine:
    - "YourBrand"
    - "YourBrand.io"

  competitors:
    - "CompetitorA"
    - "CompetitorB"
    - "IndustryTool"

intents:
  - id: "best-tools-in-category"
    prompt: "What are the best tools for [your category]?"

  - id: "comparison-query"
    prompt: "Compare the top [category] tools for [specific-use-case]"
```

### Configuration Tips

- **Brand aliases**: Include all variations of your brand name (e.g., "HubSpot", "HubSpot CRM")
- **Competitor list**: Be comprehensive - include direct and indirect competitors
- **Intent prompts**: Use natural language queries that real users would ask
- **Model selection**: Use smaller models (gpt-4o-mini, claude-haiku, grok-2-1212) for cost efficiency
- **LLM rank extraction**: Set to `true` only if regex extraction fails (costs more)

## 📖 Usage Examples

### Human Mode (Default)

Beautiful Rich output with spinners, colors, and formatted tables:

```bash
llm-answer-watcher run --config watcher.config.yaml
```

Output:
```
🔍 Running LLM Answer Watcher...
├── Query: "What are the best email warmup tools?"
├── Models: OpenAI gpt-4o-mini, Anthropic claude-3-5-haiku, Mistral mistral-large-latest
├── Brands: 2 monitored, 5 competitors
└── Output: ./output/2025-11-01T14-30-00Z/

✅ Queries completed: 6/6
💰 Total cost: $0.0142
📊 Report: ./output/2025-11-01T14-30-00Z/report.html
```

### Agent Mode (AI Automation)

Structured JSON output with no ANSI codes:

```bash
llm-answer-watcher run --config watcher.config.yaml --format json
```

Output:
```json
{
  "run_id": "2025-11-01T14-30-00Z",
  "status": "success",
  "queries_completed": 6,
  "total_cost_usd": 0.0142,
  "output_dir": "./output/2025-11-01T14-30-00Z",
  "mentions": [
    {
      "intent_id": "best-email-warmup-tools",
      "brand": "YourBrand",
      "rank_position": 1,
      "provider": "openai",
      "model": "gpt-4o-mini"
    }
  ]
}
```

### Quiet Mode (Minimal Output)

Tab-separated values for scripts and pipelines:

```bash
llm-answer-watcher run --config watcher.config.yaml --quiet
```

Output:
```
2025-11-01T14-30-00Z	success	6	0.0142	./output/2025-11-01T14-30-00Z
```

### Automation Mode (No Prompts)

Skip all confirmation prompts for CI/CD:

```bash
llm-answer-watcher run --config watcher.config.yaml --yes --format json
```

### Configuration Validation

Validate your configuration before running:

```bash
llm-answer-watcher validate --config watcher.config.yaml
```

## 📊 Output Documentation

### Directory Structure

Each run creates a timestamped directory:

```
output/
└── 2025-11-01T14-30-00Z/
    ├── run_meta.json           # Summary with costs and stats
    ├── intent_best-tools_raw_openai_gpt-4o-mini.json      # Raw LLM response
    ├── intent_best-tools_parsed_openai_gpt-4o-mini.json   # Extracted mentions
    ├── report.html             # Interactive HTML report
    └── ...                     # One file per intent/model combination
```

### SQLite Database

All data is stored in `watcher.db` for historical analysis:

```sql
-- View all runs
SELECT run_id, timestamp_utc, total_cost_usd, queries_completed
FROM runs
ORDER BY timestamp_utc DESC;

-- Track brand mentions over time
SELECT
    DATE(timestamp_utc) as date,
    brand,
    COUNT(*) as mentions,
    AVG(rank_position) as avg_rank
FROM mentions
WHERE normalized_name = 'YourBrand'
GROUP BY DATE(timestamp_utc), brand
ORDER BY date DESC;

-- Compare vs competitors
SELECT
    brand,
    COUNT(*) as total_mentions,
    AVG(rank_position) as avg_rank,
    MIN(rank_position) as best_rank
FROM mentions
WHERE run_id = '2025-11-01T14-30-00Z'
GROUP BY brand
ORDER BY avg_rank ASC;
```

### HTML Report Features

The `report.html` file includes:

- **Summary Overview**: Costs, queries completed, brands found
- **Brand Mention Tables**: Which brands appeared where
- **Rank Distribution**: Visual charts of ranking positions
- **Historical Trends**: Brand performance over time (when multiple runs exist)
- **Raw Responses**: Expandable sections to see exact LLM outputs

## 🔢 Exit Codes

The CLI uses standardized exit codes for automation:

```bash
0: Success - all queries completed successfully
1: Configuration error (invalid YAML, missing API keys)
2: Database error (cannot create/access SQLite)
3: Partial failure (some queries failed, but run completed)
4: Complete failure (no queries succeeded)
```

Use these in scripts:

```bash
llm-answer-watcher run --config watcher.config.yaml --yes
case $? in
    0) echo "✅ Success" ;;
    1) echo "❌ Configuration error" ;;
    2) echo "❌ Database error" ;;
    3) echo "⚠️  Partial failure" ;;
    4) echo "❌ Complete failure" ;;
esac
```

## 💰 Cost Estimation

The tool estimates costs before running queries:

```bash
# Example cost breakdown
├── OpenAI gpt-4o-mini: $0.0006 per query × 3 intents = $0.0018
├── Anthropic claude-3-5-haiku: $0.0008 per query × 3 intents = $0.0024
├── Grok grok-2-1212: $0.0012 per query × 3 intents = $0.0036
└── Total estimated cost: $0.0078
```

Cost factors:
- **Model pricing**: Different models have different per-token costs
- **Intent complexity**: Longer prompts may use more tokens
- **Response length**: More detailed LLM responses cost more
- **Number of brands**: More brands to analyze doesn't significantly increase cost

## 🔌 Supported Providers & Models

LLM Answer Watcher supports multiple LLM providers with a unified interface:

### OpenAI
- **Provider**: `openai`
- **Models**: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`
- **Pricing**: $0.15-$2.50 per 1M input tokens, $0.60-$10 per 1M output tokens
- **Features**: Fast, cost-effective, excellent for production use

### Anthropic (Claude)
- **Provider**: `anthropic`
- **Models**: `claude-3-5-haiku-20241022`, `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`
- **Pricing**: $0.80-$15 per 1M input tokens, $4-$75 per 1M output tokens
- **Features**: High-quality responses, strong reasoning capabilities

### X.AI (Grok)
- **Provider**: `grok`
- **Models**: `grok-beta`, `grok-2-1212`, `grok-2-latest`, `grok-3`, `grok-3-mini`
- **Pricing**: $2-$5 per 1M input tokens, $10-$25 per 1M output tokens
- **Features**: OpenAI-compatible API, real-time X platform integration

### Configuration Example

```yaml
models:
  # Cost-optimized configuration
  - provider: "openai"
    model_name: "gpt-4o-mini"
    env_api_key: "OPENAI_API_KEY"

  # High-quality configuration
  - provider: "anthropic"
    model_name: "claude-3-5-sonnet-20241022"
    env_api_key: "ANTHROPIC_API_KEY"

  # Alternative provider
  - provider: "grok"
    model_name: "grok-2-1212"
    env_api_key: "XAI_API_KEY"
```

## 🤖 Using with AI Agents

LLM Answer Watcher is designed for AI agent automation:

```python
import subprocess
import json

def run_brand_monitoring(config_path: str) -> dict:
    """Run monitoring and return structured results"""
    result = subprocess.run([
        "llm-answer-watcher", "run",
        "--config", config_path,
        "--format", "json",
        "--yes"
    ], capture_output=True, text=True)

    return json.loads(result.stdout)

# Usage
results = run_brand_monitoring("watcher.config.yaml")
print(f"Run {results['run_id']} completed with {results['queries_completed']} queries")
print(f"Total cost: ${results['total_cost_usd']:.4f}")

# Check for brand mentions
your_brand_mentions = [
    m for m in results['mentions']
    if m['brand'] in ['YourBrand', 'YourBrand.io']
]
```

## 🔒 Security Notes

- **Never commit API keys** to version control
- **Use environment variables** for all sensitive configuration
- **Local data storage** - all data stays on your machine
- **No phone home** - the tool doesn't send data anywhere except to configured LLM APIs
- **SQL injection protection** - all database queries use parameterized statements
- **Input validation** - configuration files are validated with Pydantic

### Best Practices

```bash
# Use .env files (add to .gitignore)
echo "OPENAI_API_KEY=sk-your-key" > .env
echo "ANTHROPIC_API_KEY=sk-ant-your-key" >> .env
echo "XAI_API_KEY=xai-your-key" >> .env

# Load in your shell
source .env

# Or use direnv for automatic loading
echo "source .env" > .envrc
direnv allow
```

## 📈 SQLite Query Examples

### Track Brand Performance

```sql
-- Your brand's average rank over time
SELECT
    DATE(timestamp_utc) as date,
    AVG(rank_position) as avg_rank,
    COUNT(*) as mentions
FROM mentions m
JOIN runs r ON m.run_id = r.run_id
WHERE normalized_name = 'yourbrand'
GROUP BY DATE(timestamp_utc)
ORDER BY date DESC;
```

### Competitor Analysis

```sql
-- How often competitors appear
SELECT
    brand,
    COUNT(*) as total_mentions,
    AVG(rank_position) as avg_rank,
    COUNT(DISTINCT run_id) as runs_appeared
FROM mentions
WHERE timestamp_utc > datetime('now', '-30 days')
GROUP BY brand
ORDER BY total_mentions DESC;
```

### Intent Performance

```sql
-- Which intents generate the most brand mentions
SELECT
    intent_id,
    COUNT(*) as total_mentions,
    COUNT(DISTINCT brand) as unique_brands
FROM mentions
WHERE timestamp_utc > datetime('now', '-7 days')
GROUP BY intent_id
ORDER BY total_mentions DESC;
```

### Cost Tracking

```sql
-- Weekly spending analysis
SELECT
    strftime('%Y-%W', timestamp_utc) as week,
    SUM(total_cost_usd) as weekly_cost,
    COUNT(*) as runs
FROM runs
WHERE timestamp_utc > datetime('now', '-90 days')
GROUP BY week
ORDER BY week DESC;
```

## 🧪 Evaluation Framework

LLM Answer Watcher includes a comprehensive evaluation framework to ensure extraction accuracy and quality control.

### Running Evaluations

```bash
# Run evaluation suite against test fixtures
llm-answer-watcher eval --fixtures evals/testcases/fixtures.yaml

# Run with custom database path
llm-answer-watcher eval --fixtures evals/testcases/fixtures.yaml --db eval_results.db

# JSON output for CI/CD
llm-answer-watcher eval --fixtures evals/testcases/fixtures.yaml --format json
```

### What Evaluations Test

The evaluation framework validates **extraction accuracy**, not LLM quality:

- **Mention Detection**: Does the system correctly identify brand mentions?
- **Precision/Recall**: Are false positives and false negatives minimized?
- **Rank Extraction**: Are ranking positions accurately extracted?
- **Edge Cases**: Word boundaries, case sensitivity, special characters

### Evaluation Metrics

The framework computes these metrics for each test case:

| Metric | Description | Target Threshold |
|--------|-------------|------------------|
| **Mention Precision** | Ratio of correct mentions to total mentions found | ≥ 90% |
| **Mention Recall** | Ratio of correct mentions to expected mentions | ≥ 80% |
| **Mention F1** | Harmonic mean of precision and recall | ≥ 85% |
| **Rank Accuracy** | Percentage of correctly ranked brands | ≥ 85% |
| **Brand Coverage** | Ratio of expected brands found | ≥ 90% |
| **False is_mine** | Zero tolerance for incorrectly flagged brands | 100% |

### Exit Codes for CI/CD

```bash
0: All tests passed (above thresholds)
1: Tests failed (below thresholds)
2: Configuration error
```

### Evaluation Database

All evaluation results are stored in `eval_results.db` for historical tracking:

```sql
-- View recent evaluation runs
SELECT run_id, timestamp_utc, pass_rate, total_test_cases, total_passed
FROM eval_runs
ORDER BY timestamp_utc DESC
LIMIT 10;

-- Track metric trends over time
SELECT DATE(timestamp_utc) as date,
       AVG(metric_value) as avg_value,
       COUNT(*) as count
FROM eval_results er
JOIN eval_runs r ON er.eval_run_id = r.run_id
WHERE er.metric_name = 'mention_precision'
  AND r.timestamp_utc >= datetime('now', '-30 days')
GROUP BY DATE(timestamp_utc)
ORDER BY date DESC;

-- Find failing tests
SELECT test_description,
       COUNT(*) as failed_metrics,
       GROUP_CONCAT(metric_name) as failing_metrics
FROM eval_results
WHERE overall_passed = 0
GROUP BY test_description
ORDER BY failed_metrics DESC;
```

### Adding Custom Test Cases

Create test fixtures in YAML format:

```yaml
test_cases:
  - description: "HubSpot mention detection"
    intent_id: "best-crm-tools"
    llm_answer_text: |
      The best CRM tools are:
      1. HubSpot - Great for small businesses
      2. Salesforce - Enterprise solution
      3. Pipedrive - Sales-focused CRM

    brands_mine:
      - "HubSpot"

    brands_competitors:
      - "Salesforce"
      - "Pipedrive"

    expected_my_mentions:
      - "HubSpot"

    expected_competitor_mentions:
      - "Salesforce"
      - "Pipedrive"

    expected_ranked_list:
      - "HubSpot"
      - "Salesforce"
      - "Pipedrive"
```

See [evals/README.md](evals/README.md) for complete fixture format documentation.

### Continuous Integration

The evaluation suite runs automatically on every push via GitHub Actions:

```yaml
# .github/workflows/evals.yml
- name: Run Evaluation Suite
  run: |
    uv run llm-answer-watcher eval --fixtures evals/testcases/fixtures.yaml

- name: Check Coverage
  run: |
    uv run pytest tests/test_evals.py -v
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone and install development dependencies
git clone https://github.com/nikolabalic/llm-answer-watcher.git
cd llm-answer-watcher
uv sync --dev

# Run tests
pytest

# Run tests with coverage
pytest --cov=llm_answer_watcher --cov-report=html

# Lint code
ruff check .

# Format code
ruff format .
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for beautiful CLI interfaces
- Uses [Rich](https://rich.readthedocs.io/) for terminal formatting
- Powered by [Pydantic](https://pydantic-docs.helpmanual.io/) for configuration validation
- Testing with [pytest](https://pytest.org/) and [httpx_mock](https://github.com/colin-biddle/pytest-httpx)

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/nikolabalic/llm-answer-watcher/issues)
- **Documentation**: [GitHub Wiki](https://github.com/nikolabalic/llm-answer-watcher/wiki)
- **Author**: Nikola Balić

---

**LLM Answer Watcher** - Monitor your brand's presence in AI-powered search results.
