# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Export formats: Obsidian/PKM-ready Markdown notes, JSON manifests, and executive briefs.
"""

from pathlib import Path

from .models import Episode


def export_markdown(episode: Episode, output_path: Path | str | None = None) -> str:
    """Generate PKM/Obsidian-ready Markdown document."""
    d = episode.distillation
    tags_str = " ".join([f"#{t}" for t in (d.tags if d else ["lexicast"])])
    
    quotes_md = "\n".join([f"> *\"{q}\"*" for q in (d.quotes if d else [])])
    models_md = "\n".join([f"- **{m}**" for m in (d.mental_models if d else [])])
    habits_md = "\n".join([f"- [ ] {h}" for h in (d.micro_habits if d else [])])

    md = f"""---
id: {episode.id}
title: "{episode.title}"
speaker: "{episode.speaker}"
date: {episode.created_at}
tags: [{tags_str}]
---

# 🎙️ {episode.title}
**Speaker / Guest:** `{episode.speaker}`  
**Source:** `{episode.source_uri}`  

---

## 🎯 1. Executive Thesis & Context
{d.thesis if d else "N/A"}

---

## 💬 2. Unabridged Key Quotes
{quotes_md if quotes_md else "_No quotes extracted._"}

---

## 🧠 3. Mental Models & First Principles
{models_md if models_md else "_No models extracted._"}

---

## ⚖️ 4. Moral & Philosophical Takeaways
{d.moral_philosophy if d else "N/A"}

---

## ⚡ 5. Actionable Daily Micro-Habits
{habits_md if habits_md else "_No habits generated._"}

---

### 📝 Raw Transcript Reference
<details>
<summary>Click to expand full transcript</summary>

{episode.raw_transcript}
</details>
"""
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
    return md


def format_executive_brief(episode: Episode) -> str:
    """Generate concise, high-impact executive brief formatted for chat/terminal."""
    d = episode.distillation
    if not d:
        return f"Episode [{episode.id}] {episode.title} has not been distilled yet."

    quote_str = f"\"{d.quotes[0]}\"" if d.quotes else "N/A"
    habits_str = "\n".join([f"  • {h}" for h in d.micro_habits[:2]])

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎙️ {episode.title.upper()}
Speaker: {episode.speaker} | ID: {episode.id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 CORE THESIS:
{d.thesis}

💬 KEY QUOTE:
{quote_str}

🧠 MENTAL MODELS:
{", ".join(d.mental_models)}

⚖️ MORAL LESSON:
{d.moral_philosophy}

⚡ ACTIONABLE HABITS:
{habits_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
