# Contributing to drivemesh-core

Thank you for your interest in contributing to `drivemesh-core`!

## Development Guidelines

1. **Local-First & Zero Secrets**: Ensure no credentials, API keys, or private identifiers are stored or required by default.
2. **Code Style**: We use [Ruff](https://github.com/astral-sh/ruff) for linting and code formatting.
   ```bash
   uv run --with ruff ruff check --fix src tests
   uv run --with ruff ruff format src tests
   ```
3. **Testing**: All features and fixes must include corresponding `pytest` tests with full coverage.
   ```bash
   uv run --with pytest --with pytest-cov pytest -v
   ```
4. **Commit Conventions**: Use conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`).
