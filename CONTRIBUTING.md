# Contributing to Cadence Calendar

Thank you for your interest in contributing to `cadence-calendar`!

## Code Standards
- 100% test coverage using `pytest` & `pytest-cov`.
- Linting & formatting compliance with `ruff`.
- 100% clean-room stdlib implementation with zero mandatory cloud dependencies.
- Zero hardcoded secrets, credentials, or private calendar URLs.

## Development Workflow
```bash
git checkout -b feature/your-feature
uv run --with ruff ruff check --fix src tests
uv run --with ruff ruff format src tests
uv run --with pytest --with pytest-cov pytest -v
```
