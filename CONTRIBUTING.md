# Contributing to lexicast-engine

Thank you for contributing to `lexicast-engine`!

## Development Setup

```bash
git clone https://github.com/Muybi3n/AI_Projects.git
cd AI_Projects
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Quality Checks

```bash
pytest
ruff check src tests
```
