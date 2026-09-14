# Contributing to inboxguard-core

Thank you for your interest in improving `inboxguard-core`!

## Code Quality Standards
1. **100% Local-First & Zero-Credential Philosophy:** All parsers and heuristic classifiers must run entirely offline without requiring network connectivity, API keys, or external daemon dependencies.
2. **Formatting & Linting:** Code must be formatted and linted with `ruff`:
   ```bash
   uv run --with ruff ruff check --fix src tests
   uv run --with ruff ruff format src tests
   ```
3. **Full Test Coverage:** All features and fixes must include pytest suites:
   ```bash
   uv run --with pytest --with pytest-cov pytest -v
   ```
4. **Security & Privacy:** Ensure no PII, API tokens, passwords, or personal credentials are hardcoded or leaked into git history.
