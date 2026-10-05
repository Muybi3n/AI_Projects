# Contributing to subwatch-engine

Thank you for your interest in contributing to `subwatch-engine`!

## Development Guidelines

1. **Local-First & Privacy First**:
   - Zero telemetry or phone-home requests.
   - All financial and subscription metadata stays strictly on local storage (`~/.subwatch/`).

2. **Code Standards**:
   - Python 3.10+ compatible.
   - Format and lint with `ruff`:
     ```bash
     uv run --with ruff ruff check --fix src tests
     uv run --with ruff ruff format src tests
     ```
   - 100% test coverage with `pytest`:
     ```bash
     uv run --with pytest --with pytest-cov pytest -v
     ```
