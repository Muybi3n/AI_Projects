# Contributing to CanaryMesh

Thank you for your interest in contributing to CanaryMesh! This project provides local-first defensive deception, decoy honey-tokens, and cryptographic integrity tripwires.

## Core Directives

1. **Defensive Deception Only:** CanaryMesh is strictly a defensive canary tripwire framework. All decoys are non-functional honey-tokens designed to detect unauthorized host reconnaissance or tampering.
2. **100% Local-First:** No telemetry, no remote cloud dependencies, no mandatory external accounts.
3. **Clean Code & Rigorous Testing:** All PRs must pass `ruff` formatting/linting and maintain test coverage.

## Development Setup

```bash
git clone git@github.com:Muybi3n/AI_Projects.git
cd AI_Projects
git checkout canarymesh-core

pip install -e .[dev]

# Run linting and tests
ruff check src tests
ruff format --check src tests
pytest --cov=canarymesh -v
```
