# Development Setup

Set up your development environment for contributing.

## Prerequisites

- Python 3.12 or 3.13
- Git
- uv or pip

## Clone and Install

```bash
# Clone repository
git clone https://github.com/nibzard/llm-answer-watcher.git
cd llm-answer-watcher

# Install with uv (recommended)
uv sync --dev

# Or with pip
pip install -e ".[dev]"
```

## Development Tools

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=llm_answer_watcher --cov-report=html

# Run specific test
pytest tests/test_config_loader.py::test_load_valid_config
```

### Linting

```bash
# Check code quality
ruff check .

# Auto-fix issues
ruff check . --fix

# Format code
ruff format .
```

### Documentation

```bash
# Build docs
mkdocs build

# Serve docs locally
mkdocs serve
```

## Making Changes

1. Create a branch: `git checkout -b feature/my-feature`
1. Make changes
1. Run tests: `pytest`
1. Run linting: `ruff check .`
1. Commit: `git commit -m "feat: add feature"`
1. Push: `git push origin feature/my-feature`
1. Create Pull Request

See [Code Standards](../code-standards/) for coding guidelines.
