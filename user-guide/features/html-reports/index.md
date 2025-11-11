# HTML Reports

Auto-generated interactive HTML reports for each monitoring run.

## Features

- Brand mention visualization
- Rank distribution charts
- Cost breakdowns
- Raw response inspection
- Historical trends (if multiple runs)

## Report Location

```text
output/YYYY-MM-DDTHH-MM-SSZ/report.html
```

## Opening Reports

```bash
# macOS
open output/2025-11-05T14-30-00Z/report.html

# Linux
xdg-open output/2025-11-05T14-30-00Z/report.html
```

## Report Sections

1. **Summary**: Costs, queries, brands found
1. **Brand Mentions**: Detailed mention tables
1. **Rank Distribution**: Visual charts
1. **Historical Trends**: Performance over time
1. **Raw Responses**: Full LLM outputs
