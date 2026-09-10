# Contributing to sparsededup

Thank you for your interest in contributing to `sparsededup`! We welcome contributions, bug reports, feature requests, and performance optimizations.

---

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Muybi3n/sparsededup.git
   cd sparsededup
   ```

2. **Set up a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install editable package with dev dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run test suite & linter:**
   ```bash
   pytest
   ruff check src tests
   ```

---

## Code Style & Standards

- Follow PEP 8 and use `ruff` for linting.
- Keep the core engine dependency-free (standard library only) for maximum portability across bare-metal environments and container hosts.
- Add unit tests for any new CLI flags, hashing mechanisms, or action handlers.
- Verify multi-platform path compatibility (`pathlib.Path`).

---

## Submitting Pull Requests

1. Fork the repository and create your feature branch: `git checkout -b feat/my-feature`.
2. Commit your changes with clear commit messages.
3. Push to your fork: `git push origin feat/my-feature`.
4. Open a Pull Request on GitHub against `main`.
