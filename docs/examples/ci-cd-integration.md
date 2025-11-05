# CI/CD Integration

Integrate brand monitoring into your continuous integration pipeline.

## GitHub Actions Example

`.github/workflows/monitoring.yml`:

```yaml
name: Brand Monitoring

on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install
        run: |
          pip install uv
          uv sync

      - name: Run monitoring
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          uv run llm-answer-watcher run             --config config.yaml             --yes             --format json

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: results
          path: output/
```

## Exit Code Handling

```yaml
- name: Run monitoring
  id: monitor
  run: |
    uv run llm-answer-watcher run --config config.yaml --yes
    echo "exit_code=$?" >> $GITHUB_OUTPUT
  continue-on-error: true

- name: Check result
  run: |
    if [ "${{ steps.monitor.outputs.exit_code }}" == "0" ]; then
      echo "Success"
    else
      echo "Failed"
      exit 1
    fi
```

See [Automation](../user-guide/usage/automation.md) for more examples.
