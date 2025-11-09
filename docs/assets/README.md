# Documentation Assets

This directory contains images and media files for the documentation.

## Demo Recording

### Current Status

- ⏳ **demo.gif**: Placeholder (needs to be recorded)
- ✅ **demo-placeholder.svg**: Temporary placeholder image

### Recording the Demo

To create the actual `demo.gif`:

```bash
# Quick method
./scripts/record-demo.sh

# Or follow the detailed guide
# See: ../DEMO_RECORDING.md
```

### Requirements

The `demo.gif` should:

- Show the `python -m llm_answer_watcher demo` command
- Display the full demo output (brand detection, ranking, cost)
- Be optimized (< 5MB for GitHub)
- Use dark terminal theme for consistency
- Dimensions: ~1000x600px (100 cols × 30 rows terminal)

### Tools Used

- **asciinema**: Terminal session recording
- **agg**: Convert asciinema recordings to GIF
- **gifsicle**: GIF optimization

### Once Recorded

1. Replace `demo-placeholder.svg` with actual `demo.gif`
2. Update references in documentation
3. Commit and push:

```bash
git add docs/assets/demo.gif
git commit -m "docs: add actual demo.gif recording"
git push
```

## File Structure

```
docs/assets/
├── README.md              # This file
├── demo-placeholder.svg   # Temporary placeholder (remove after recording)
└── demo.gif              # Actual demo recording (to be created)
```

## Guidelines

### Image Optimization

- **GIFs**: Optimize with gifsicle (`-O3 --lossy=80`)
- **PNGs**: Optimize with pngcrush or optipng
- **SVGs**: Minify with svgo

### File Size Limits

- GIFs: < 5MB (GitHub limit)
- PNGs: < 1MB per image
- SVGs: < 500KB per file

### Naming Convention

- Use lowercase
- Use hyphens for spaces
- Descriptive names: `feature-name-screenshot.png`
- Version suffix if needed: `demo-v2.gif`
