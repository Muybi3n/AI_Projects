# Contributing to ShelfWise

Thank you for your interest in contributing to `shelfwise-core`!

## Development Guidelines

1. **Local-First & Privacy First**:
   - Zero telemetry or phone-home requests.
   - All hardware specs, serial numbers, and receipts remain strictly on local storage (`~/.shelfwise/`).

2. **Code Standards**:
   - Python 3.10+ compatible.
   - Format and lint with `ruff`:
     ```bash
     uv run --with ruff ruff check --fix src tests
     uv run --with ruff ruff format src tests
     ```
   - 100% test pass rate with `pytest`:
     ```bash
     uv run --with pytest --with pytest-cov pytest -v
     ```

3. **Submitting Changes**:
   - Open a pull request against the `shelfwise-core` branch with conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`).
