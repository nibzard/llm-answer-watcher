# Changelog

All notable changes to LLM Answer Watcher will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive MkDocs documentation with Material theme
- Post-intent operations for dynamic workflows
- Function calling support for improved extraction accuracy
- Brand visibility score in reports

### Changed
- Improved test coverage to 100% for core modules
- Enhanced error messages for better debugging

## [0.1.0] - 2025-11-05

### Added
- Initial release of LLM Answer Watcher
- Multi-provider support: OpenAI, Anthropic, Mistral, X.AI Grok, Google Gemini, Perplexity
- Brand mention detection with word-boundary matching
- Rank extraction (pattern-based and LLM-assisted)
- SQLite database for historical tracking
- HTML report generation with Jinja2
- Dual-mode CLI (human-friendly Rich output, structured JSON for automation)
- Budget controls and cost estimation
- Dynamic pricing from llm-prices.com with 24-hour caching
- Web search cost calculation for OpenAI models
- Retry logic with exponential backoff
- Evaluation framework for extraction accuracy
- Configuration validation with Pydantic
- Exit codes for automation (0-4)
- Example configurations
- Comprehensive test suite (750+ tests)
- GitHub Actions CI/CD pipeline

### Core Modules
- `config/`: YAML loading and Pydantic validation
- `llm_runner/`: Multi-provider LLM client abstraction
- `extractor/`: Brand mention detection and rank extraction
- `storage/`: SQLite schema and JSON writers
- `report/`: HTML report generation
- `utils/`: Time utilities, logging, cost estimation, Rich console
- `evals/`: Evaluation framework

### Supported Models
- **OpenAI**: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
- **Anthropic**: claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus
- **Mistral**: mistral-large-latest, mistral-small-latest
- **X.AI**: grok-beta, grok-2-1212, grok-2-latest, grok-3
- **Google**: gemini-2.0-flash-exp, gemini-1.5-pro, gemini-1.5-flash
- **Perplexity**: sonar, sonar-pro, sonar-reasoning

### Documentation
- README with quick start and examples
- CLAUDE.md with development guidelines
- CONTRIBUTING.md with contribution guidelines
- SPECS.md with complete engineering specification
- TODO.md with milestone tracking

### Security
- Environment variable-based API key management
- SQL injection prevention (parameterized queries)
- XSS prevention (Jinja2 autoescaping)
- No API key logging

## Release Notes

### Version 0.1.0 - Production Ready

This is the first production-ready release of LLM Answer Watcher. The tool is feature-complete for core brand monitoring use cases:

**Highlights**:
- ✅ 8,200 lines of production Python code
- ✅ 17,400 lines of test code (750+ tests)
- ✅ 100% coverage on critical paths
- ✅ 6 LLM providers supported
- ✅ Complete evaluation framework
- ✅ Full documentation

**What's Working**:
- All core features tested and validated
- Multi-provider queries with retry logic
- Accurate brand mention detection (90%+ precision)
- Historical tracking in SQLite
- Professional HTML reports
- Budget protection
- CI/CD integration

**Known Limitations**:
- No async support (intentionally - keeping it simple)
- Web search only for OpenAI models
- Perplexity request fees not yet in cost estimates
- Trends command not yet implemented (data collection works)

**Upgrade Notes**:
- This is the initial release - no upgrades needed
- SQLite schema version 1
- Configuration format stable

## Future Roadmap

### Planned Features

**v0.2.0** (Q1 2025):
- `trends` command for historical analysis
- Dashboard UI for visualizing trends
- DeepEval integration for quality metrics
- Async support for parallel queries
- Enhanced web search support

**v0.3.0** (Q2 2025):
- Cloud deployment option
- HTTP API (expose internal contract)
- Real-time alerts and webhooks
- Advanced analytics and insights
- Multi-user support

**v1.0.0** (Q3 2025):
- Enterprise features
- Advanced provider integrations
- Custom model support
- White-label options
- SaaS offering

## Contributing

We welcome contributions! See [CONTRIBUTING.md](contributing/development-setup.md) for guidelines.

## Links

- **Repository**: [github.com/nikolabalic/llm-answer-watcher](https://github.com/nikolabalic/llm-answer-watcher)
- **Issues**: [github.com/nikolabalic/llm-answer-watcher/issues](https://github.com/nikolabalic/llm-answer-watcher/issues)
- **Documentation**: This site
- **License**: MIT
