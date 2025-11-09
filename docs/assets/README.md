# Documentation Assets

This directory contains images and media files for the documentation.

## Demo Recording

### Current Status

- ✅ **demo.gif**: Active demo recording (266KB, 688x490px)
  - Shows brand monitoring workflow
  - Created with asciinema
  - Optimized for GitHub

### Updating the Demo

To update `demo.gif` with a new recording:

```bash
# Quick method
./scripts/record-demo.sh

# Or follow the detailed guide
# See: ../DEMO_RECORDING.md
```

### Current Demo Specifications

The existing `demo.gif`:

- **Size**: 266KB (well under 5MB GitHub limit)
- **Dimensions**: 688×490 pixels
- **Format**: GIF (version 89a)
- **Content**: Terminal recording showing validation & execution
- **Created with**: asciinema + agg converter

### Requirements for New Recordings

When creating a new `demo.gif`:

- Show the `python -m llm_answer_watcher demo` command
- Display the full demo output (brand detection, ranking, cost)
- Keep optimized (< 5MB for GitHub)
- Use dark terminal theme for consistency
- Target dimensions: ~700x500px or 1000x600px

### Tools Used

- **asciinema**: Terminal session recording
- **agg**: Convert asciinema recordings to GIF
- **gifsicle**: GIF optimization

## File Structure

```
docs/assets/
├── README.md    # This file
└── demo.gif     # Active demo recording
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
