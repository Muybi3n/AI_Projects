# Contributing to capdrift-engine

Thank you for your interest in contributing to `capdrift-engine`!

## Setup

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
