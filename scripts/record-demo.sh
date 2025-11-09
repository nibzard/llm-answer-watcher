#!/bin/bash
# Script to record demo.gif for LLM Answer Watcher
# Requires: asciinema and agg (asciinema gif generator)
#
# Installation:
#   brew install asciinema
#   cargo install --git https://github.com/asciinema/agg
#
# Or use Docker:
#   docker run --rm -it -v $PWD:/data asciinema/asciinema

set -e

echo "🎬 Recording LLM Answer Watcher demo..."

# Record with asciinema
asciinema rec demo.cast \
  --overwrite \
  --title "LLM Answer Watcher Demo" \
  --command "python -m llm_answer_watcher demo" \
  --idle-time-limit 2

echo ""
echo "✅ Recording complete! Converting to GIF..."

# Convert to GIF using agg
agg demo.cast docs/assets/demo.gif \
  --theme monokai \
  --font-family "JetBrains Mono, Fira Code, Monaco, monospace" \
  --font-size 14 \
  --line-height 1.4 \
  --cols 100 \
  --rows 30 \
  --speed 1.5

echo "✅ GIF created at docs/assets/demo.gif"
echo ""
echo "📏 GIF size:"
ls -lh docs/assets/demo.gif

# Optimize GIF (optional - requires gifsicle)
if command -v gifsicle &> /dev/null; then
  echo ""
  echo "🔧 Optimizing GIF..."
  gifsicle -O3 --lossy=80 -o docs/assets/demo-optimized.gif docs/assets/demo.gif
  mv docs/assets/demo-optimized.gif docs/assets/demo.gif
  echo "✅ GIF optimized!"
  ls -lh docs/assets/demo.gif
fi

echo ""
echo "🎉 Demo recording complete!"
echo "   Location: docs/assets/demo.gif"
echo ""
echo "Next steps:"
echo "  1. git add docs/assets/demo.gif"
echo "  2. git commit -m 'docs: add demo.gif recording'"
echo "  3. git push"
