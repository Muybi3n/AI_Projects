# Contributing to nasroute-core

Thank you for your interest in contributing to `nasroute-core`!

## Code of Conduct
We adhere to standard open-source best practices. All contributions must remain strictly legal, professional, and enterprise-defensible.

## Development Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/Muybi3n/AI_Projects.git
   cd AI_Projects
   git checkout nasroute-core
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```
3. Run tests and linter:
   ```bash
   ruff check src tests
   ruff format --check src tests
   pytest -v --cov=nasroute
   ```

## Pull Request Guidelines
- Follow standard conventional commit formats (`feat:`, `fix:`, `docs:`, `test:`).
- Ensure 100% test coverage for any new features or bug fixes.
- Zero hardcoded secrets, API tokens, or internal IP references.
