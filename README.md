<div align="center">
  <div>&nbsp;</div>
  <h1>🚀 AI Projects & Engineering Portfolio</h1>
  <p><strong>A Showcase of Local-First, Privacy-Preserving AI Engines, Data Systems & Utility Tools</strong></p>

  [![CI Pipeline](https://img.shields.io/badge/CI-Passing-success?style=flat-square&logo=github-actions)](https://github.com/Muybi3n/AI_Projects/actions)
  [![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue?style=flat-square&logo=python)](#)
  [![Code Style](https://img.shields.io/badge/Code%20Style-Ruff-000000?style=flat-square)](https://github.com/astral-sh/ruff)
  [![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
  [![Built For](https://img.shields.io/badge/Architecture-100%25%20Local--First-orange?style=flat-square)](#)
</div>

---

## 🌟 Welcome to the Portfolio!

This repository hosts a curated collection of production-grade, local-first Python packages. Each project is designed with **zero hardcoded credentials**, **offline-first deterministic math/logic**, **SQLite FTS5 full-text search**, and **pluggable local/cloud AI companion capabilities** (supporting Ollama, vLLM, and OpenAI-compatible endpoints).

---

## 🗂️ Portfolio Project Directory

| Project | Domain | Key Capabilities | Branch Link |
| :--- | :--- | :--- | :--- |
| **`sparsededup`** | Storage & Systems | 3-Point Sparse-Block BLAKE2b/SHA-256 deduplication for multi-terabyte arrays. | [`main`](https://github.com/Muybi3n/AI_Projects/tree/main) |
| **`flowbalance-core`** | Personal Finance | Deterministic cash flow forecasting, solvency runway stress-testing, FTS5 search & AI advisor. | [`flowbalance-core`](https://github.com/Muybi3n/AI_Projects/tree/flowbalance-core) |
| **`capdrift-engine`** | Investment Portfolios | Broker CSV ingestion (Robinhood, Schwab, etc.), HHI concentration, drift rebalancing & dividend snowball. | [`capdrift-engine`](https://github.com/Muybi3n/AI_Projects/tree/capdrift-engine) |
| **`trustguard-core`** | Wills, Trusts & Family Planning | Schedule A asset titling, probate risk detection, beneficiary waterfalls, minor guardianship & fiduciary logs. | [`trustguard-core`](https://github.com/Muybi3n/AI_Projects/tree/trustguard-core) |
| **`careguard-core`** | Family Caregiving & Medical Records | Multi-doctor coordinator, 4-slot pillbox scheduler, vitals anomaly detection, HIPAA PHI redaction & 1-page clinical visit briefing sheet. | [`careguard-core`](https://github.com/Muybi3n/AI_Projects/tree/careguard-core) |
| **`oncorenal-core`** | Oncology & Renal / Dialysis | Chemo cycle nadir immune tracker, neutropenic fever alerts, CTCAE toxicity grading, dialysis IDWG/dry-weight fluid ledger & renal macro limits. | [`oncorenal-core`](https://github.com/Muybi3n/AI_Projects/tree/oncorenal-core) |
| **`medcadence-core`** | Healthcare & Telemetry | Lab bloodwork biomarker tracking, medication/supplement interaction safety checks & emergency cards. | [`medcadence-core`](https://github.com/Muybi3n/AI_Projects/tree/medcadence-core) |
| **`lexicast-engine`** | Audio NLP & Knowledge | 5-Layer podcast audio transcription distillation and BM25 full-text search indexing. | [`lexicast-engine`](https://github.com/Muybi3n/AI_Projects/tree/lexicast-engine) |

---

## ⚡ 60-Second Quickstart (Beginner-Friendly)

All projects follow modern Python standards and require **Python 3.10+**.

### Step 1: Clone the Repository
```bash
git clone https://github.com/Muybi3n/AI_Projects.git
cd AI_Projects
```

### Step 2: Switch to Any Project Branch
```bash
# Example: Switch to the Healthcare project
git checkout medcadence-core

# Or switch to the Wills & Trusts project
git checkout trustguard-core

# Or switch to the Investment Portfolio Companion
git checkout capdrift-engine

# Or switch to Cash Flow & Finance
git checkout flowbalance-core
```

### Step 3: Install in 1 Command
```bash
pip install -e .
```

---

## 📖 Quick Interactive Examples

### 1. 💰 Personal Cash Flow & Solvency (`flowbalance-core`)
```bash
git checkout flowbalance-core && pip install -e .

# Add your checking balance and monthly rent
flowbalance account add --name "Primary Checking" --balance 8500
flowbalance expense add --name "Rent & Utilities" --amount 2200 --frequency monthly

# Forecast your cash runway for the next 180 days
flowbalance forecast --days 180

# Ask the AI financial advisor
flowbalance ask "How long is my runway if I cut discretionary spending by 30%?"
```

### 2. 🧭 Investment Portfolio Companion (`capdrift-engine`)
```bash
git checkout capdrift-engine && pip install -e .

# Ingest your downloaded broker CSV (Robinhood, Charles Schwab, Fidelity, etc.)
capdrift ingest portfolio.csv --broker Robinhood

# Run a complete health, concentration, and allocation drift audit
capdrift audit

# Simulate compounding dividend growth over 5 years
capdrift dividends --years 5

# Ask the AI portfolio companion
capdrift ask "Where is my biggest uncompensated risk?"
```

### 3. 🏛️ Wills, Trusts & Family Planning (`trustguard-core`)
```bash
git checkout trustguard-core && pip install -e .

# Initialize your family trust
trustguard init --name "The Henderson Family Revocable Living Trust" --grantor "Robert Henderson"

# Add a house and audit probate court risk
trustguard asset add --name "Family Home" --category real_estate --value 750000 --titling titled_to_trust
trustguard asset add --name "LLC Business Equity" --category business_equity_llc --value 300000 --titling unfunded_probate_risk
trustguard asset audit

# Add minor child guardianship directive
trustguard guardianship add --child "Oliver Henderson" --guardian "Uncle David" --alternate "Aunt Sarah"

# Ask the AI estate companion
trustguard ask "What steps must the trustee take to avoid probate?"
```

### 4. 🩺 Healthcare Telemetry & Lab Tracker (`medcadence-core`)
```bash
git checkout medcadence-core && pip install -e .

# Initialize your profile
medcadence init --label "Alex" --sex male --birth-year 1990

# Log bloodwork results (e.g. LDL cholesterol)
medcadence lab add --name "LDL Cholesterol" --value 135 --high 100 --unit "mg/dL"
medcadence lab trends

# Audit your prescriptions and OTC supplements for dangerous interactions
medcadence med add --name "Atorvastatin" --dosage "20mg"
medcadence med add --name "Grapefruit Juice" --supplement
medcadence med audit

# Ask the AI healthcare companion
medcadence ask "What questions should I ask my doctor about my lipid panel?"
```

### 5. ⚡ Sparse Storage Deduplicator (`sparsededup` - On `main` branch)
```bash
git checkout main && pip install -e .

# Run a safe dry-run scan across a media folder to find duplicate files
sparsededup /path/to/media/folder --dry-run
```

---

## 🤖 Connecting Your Own Local AI / LLM (Ollama, vLLM, OpenAI)

Every project in this repository includes a **zero-configuration offline heuristic engine** that works 100% out-of-the-box with **no API keys required**.

If you wish to connect your own local LLM (such as **Ollama** running `llama3.2` or `mistral`) or a cloud LLM:

```python
# Example: Custom 3-line Ollama adapter in Python
import requests

def my_ollama_adapter(query: str, context: dict) -> str:
    prompt = f"System Context: {context}\n\nUser Question: {query}"
    res = requests.post("http://localhost:11434/api/generate", json={"model": "llama3.2", "prompt": prompt, "stream": False})
    return res.json()["response"]

# Pass it to any engine:
# from medcadence.advisor import HealthAdvisor
# advisor = HealthAdvisor(custom_llm_callable=my_ollama_adapter)
```

---

## ⚖️ Disclaimer & Standards

* **Proof of Concept Notice:** All software tools are provided for educational, informational, and exploratory modeling purposes.
* **No Financial, Legal, or Medical Advice:** None of the tools constitute financial planning, legal counsel, or medical diagnosis. Always consult licensed professionals (CPAs, Attorneys, Physicians).
* **Trademark Hygiene:** All referenced company, broker, lab, and product names (Robinhood, Schwab, Apple Health, Quest, etc.) are property of their respective trademark holders. Use is strictly for identification and compatibility.

---

## 📜 License

All projects in this repository are open source and released under the [MIT License](LICENSE).
