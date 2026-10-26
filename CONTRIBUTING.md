# Contributing to PromptGuard Proxy

Thank you for your interest in improving PromptGuard Proxy! We welcome contributions that align with our core focus: privacy-first, 100% offline security engineering and local LLM defense tooling.

## Ground Rules
1. **Safety First**: No malware samples, offensive exploits, or active bypasses intended for malicious activities.
2. **Standard Library Focused**: Keep core dependencies zero-external where feasible.
3. **Strict Code Quality**: All contributions must pass `ruff check`, `ruff format`, and have comprehensive unit test coverage with `pytest`.
4. **No Hardcoded Secrets**: Ensure test files never contain actual credentials, tokens, or PII.

## Development Workflow
1. Fork and create a topic branch.
2. Install in editable mode: `pip install -e .[dev]`
3. Run test suite: `pytest --cov=promptguard`
4. Submit PR with detailed justification.
