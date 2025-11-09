# Recording the Demo GIF

This guide explains how to record and update the demo.gif for the documentation.

## Quick Method (Recommended)

Use the provided recording script:

```bash
# Install dependencies first (see below)
./scripts/record-demo.sh
```

This will:
1. Record a terminal session running `python -m llm_answer_watcher demo`
2. Convert it to an optimized GIF
3. Save it to `docs/assets/demo.gif`

## Manual Method

### 1. Install Required Tools

#### Option A: Using Homebrew (macOS/Linux)

```bash
# Install asciinema for recording
brew install asciinema

# Install agg for GIF conversion
cargo install --git https://github.com/asciinema/agg

# Optional: Install gifsicle for optimization
brew install gifsicle
```

#### Option B: Using npm

```bash
# Install terminalizer
npm install -g terminalizer

# Record with terminalizer
terminalizer record demo
# Then: python -m llm_answer_watcher demo
# Press Ctrl+D to stop

# Render to GIF
terminalizer render demo -o docs/assets/demo.gif
```

### 2. Record the Demo

#### Using asciinema + agg:

```bash
# Record terminal session
asciinema rec demo.cast --overwrite

# Run the demo command in the recording
python -m llm_answer_watcher demo

# Press Ctrl+D to finish recording

# Convert to GIF
agg demo.cast docs/assets/demo.gif \
  --theme monokai \
  --font-size 14 \
  --line-height 1.4 \
  --cols 100 \
  --rows 30 \
  --speed 1.5
```

#### Using terminalizer:

```bash
# Initialize config (first time only)
terminalizer init

# Record
terminalizer record demo

# In the recording, run:
python -m llm_answer_watcher demo

# Render
terminalizer render demo -o docs/assets/demo.gif --quality 80
```

### 3. Optimize the GIF

```bash
# Reduce file size while maintaining quality
gifsicle -O3 --lossy=80 -o docs/assets/demo-optimized.gif docs/assets/demo.gif
mv docs/assets/demo-optimized.gif docs/assets/demo.gif
```

### 4. Verify and Commit

```bash
# Check file size (should be under 5MB for GitHub)
ls -lh docs/assets/demo.gif

# Add to git
git add docs/assets/demo.gif
git commit -m "docs: add demo.gif recording"
git push
```

## Recording Tips

### Terminal Settings

For best results, configure your terminal before recording:

```bash
# Set terminal size (recommended)
resize -s 30 100  # 30 rows, 100 columns

# Use a clean shell prompt
export PS1="$ "

# Clear terminal
clear
```

### Demo Script

Record showing these steps:

1. **Start**: Clear screen, show prompt
2. **Run**: `python -m llm_answer_watcher demo`
3. **Wait**: Let the demo run completely (shows loading, results, etc.)
4. **Finish**: Demo exits cleanly

### Timing

- Total length: ~30-45 seconds
- Use `--speed 1.5` in agg to speed up slightly
- Use `--idle-time-limit 2` to remove long pauses

## Troubleshooting

### GIF too large (>5MB)

```bash
# Further compress
gifsicle -O3 --lossy=100 --colors 128 -o demo.gif demo.gif

# Or reduce dimensions
gifsicle --resize 80% -o demo.gif demo.gif
```

### Text too small

```bash
# Re-render with larger font
agg demo.cast demo.gif --font-size 16
```

### Colors look wrong

```bash
# Try different themes
agg demo.cast demo.gif --theme dracula
# Available: monokai, dracula, nord, solarized-dark, etc.
```

## Alternative: Screen Recording

If the above tools don't work, you can use screen recording:

1. Record your terminal with QuickTime/OBS/etc.
2. Convert to GIF with: `ffmpeg -i recording.mov -vf "fps=10,scale=1000:-1" demo.gif`
3. Optimize with gifsicle

## References

- [asciinema](https://asciinema.org/)
- [agg (asciinema gif generator)](https://github.com/asciinema/agg)
- [terminalizer](https://terminalizer.com/)
- [gifsicle](https://www.lcdf.org/gifsicle/)
