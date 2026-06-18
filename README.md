# Daily Math Homework Generator

A Streamlit app that generates Grade 5 math homework PDFs for Jessie, tracks daily progress, and runs Sunday review sessions targeting past mistakes.

## Features

- Daily Grade 5 math homework following CCSS standards — one generation per day (idempotent/cached)
- Daily math/science academic vocabulary practice — 20 words with matching, fill-in-the-blank, and reading-bridge questions
- Questions and answers in separate PDFs stored under the scoped daily task tree
- Per-question ✓/✗ marking with real-time score tracking
- Sunday review: collects incorrectly marked questions from the past 7 days; skipped if no mistakes
- Weekly feedback report and skills analysis generated on Sundays; browseable by past week via date selector
- Four AI providers: DeepSeek API, Gemini API, Claude API, or local MLX server (Qwen)

---

## System Design

```
┌───────────────────────────────────────────────────────────┐
│                        Streamlit UI                       │
│   ┌──────────┐    ┌──────────┐    ┌─────────────────────┐ │
│   │  Today   │    │ History  │    │      Analysis       │ │
│   └────┬─────┘    └────┬─────┘    └──────────┬──────────┘ │
└────────┼───────────────┼─────────────────────┼────────────┘
         │               │                     │
┌────────▼───────────────▼─────────────────────▼────────────┐
│                        Services                           │
│  generator · review_service · analysis_service            │
│  feedback_service · feedback_report_service · dedup       │
└──────────────┬────────────────────────────────────────────┘
               │
    ┌──────────▼──────────────────────────────────────────┐
    │                     Storage                         │
    │                                                     │
    │  mark_buffer  ◄── single source of truth            │
    │      │                                              │
    │  mark_flusher (daemon, 5s timestamp-based flush)    │
    │      │                                              │
    │  homework_store  ·  history_store                   │
    └──────────────────────────┬──────────────────────────┘
                               │
              ┌────────────────┼───────────────┐
              ▼                ▼               ▼
         Providers           PDF           output/raw/
       AnthropicAPI      questions         YYYY/MM/DD/
       DeepSeek/Gemini/Claude/MLX      answers
```

---

## Mark Buffer — Single Source of Truth

All question state lives in one in-memory hashmap. The UI **never reads from disk at runtime** — only from the buffer.

```
mark_buffer._store = {
  "2026-04-06": {
    "marks": {
      "p1_001": True,    ← correct
      "p1_002": False,   ← wrong
      "p1_003": None,    ← not yet marked
      ...
    },
    "last_update": "2026-04-06T18:30:00.123"   ← "" if loaded from disk (not dirty)
  },
  "2026-04-07": { ... },
  ...
}
```

**Lifecycle:**

```
App startup
  → migrate_from_old_history()       one-time: converts old data/history.json
  → hydrate_all_marks()              scan all output/raw/*/*/*/homework.json
  → init_date(date, marks)           buffer populated with True/False/None per question
  → last_update = ""                 not dirty — no flush triggered

User marks a question
  → set_mark(date, qid, True/False)
  → buffer updated instantly
  → last_update = now

Background flusher (every 5s)
  → get_recently_updated(5s)         scan buffer: dates with last_update within 5s
  → _write_marks()                   full overwrite of homework.json correct fields
  → homework["last_update"] = ts     timestamp written to disk

UI reads (score bar, badges, analysis page)
  → get_marks(date) from buffer
  → calc_auto_score() = correct / total_questions (includes unchecked in denominator)
  → no disk reads, no fallbacks
```

**Design rationale:**
- Single source of truth — no split brain between memory and disk
- Timestamp-based flush: no separate dirty set to lose on exception
- Full overwrite per date keeps disk state simple and consistent
- `None` in buffer = unchecked → score denominator is always all questions

---

## Daily Task Storage

New generated work uses a scoped daily task tree so multiple subjects can share
the same app structure without colliding by date:

```
output/tasks/
└── math/
    └── homework/
        ├── raw/YYYY/MM/DD/task.json
        ├── raw/YYYY/MM/DD/meta.json
        └── pdf/YYYY/MM/DD/questions.pdf
└── english/
    └── vocabulary/
        ├── raw/YYYY/MM/DD/task.json
        ├── raw/YYYY/MM/DD/meta.json
        └── pdf/YYYY/MM/DD/vocabulary.pdf
```

Older math homework files are still read from the legacy layout for history
compatibility:

```
output/raw/
└── 2026/
    └── 04/
        ├── 06/
        │   ├── homework.json         ← questions, answers, marks, last_update
        │   ├── fingerprints.json     ← MD5 hashes for dedup
        │   ├── analysis.json         ← weekly analysis (Sundays only)
        │   └── feedback_report.json  ← weekly feedback report (Sundays only)
        └── 07/
            ├── homework.json
            └── fingerprints.json
```

`history_store` scans both the new math task tree and legacy tree at runtime:
- `get_all_dates()` → scoped math tasks plus legacy `questions.json`
- `get_total_days()` → max `day` field across non-review sessions
- `get_all_fingerprints()` → union of all per-day `fingerprints.json`
- `get_recent_topics(14)` → topics from past 14 days' homework.json
- `get_weekly_logs(date, 7)` → log entries built from homework.json + mark_buffer scores

**Scores are never stored** — always computed live from mark_buffer.

---

## Layer Responsibilities

| Layer | Path | Responsibility |
|-------|------|----------------|
| **UI** | `ui/pages/`, `ui/components/` | Streamlit pages and marking widgets |
| **Services** | `services/` | Business logic — generation, dedup, scoring, review |
| **Providers** | `providers/` | AI model abstraction (Claude API / Gemini API / local MLX) |
| **Storage** | `storage/` | Mark buffer (source of truth), JSON I/O, flush thread |
| **PDF** | `pdf/` | ReportLab PDF generation (questions and answers separate) |
| **Prompts** | `prompts/` | Prompt builders for each generation task |
| **Config** | `config/` | Curriculum instruction files (Markdown) |

---

## File Structure

```
top-math/
├── app.py                              # Entry point (1 line: render())
├── requirements.txt
├── config/
│   ├── instruction.md                 # Homework generation curriculum prompt
│   ├── review_instruction.md          # Sunday review prompt
│   ├── analysis_instruction.md        # Weekly skills analysis prompt
│   └── feedback_report_instruction.md # Weekly feedback report prompt
├── providers/
│   ├── base.py                        # Abstract ModelProvider
│   ├── anthropic_provider.py          # Claude API
│   ├── deepseek_provider.py           # DeepSeek API
│   ├── gemini_provider.py             # Gemini API
│   └── mlx_provider.py               # Local Qwen via mlx_lm server
├── prompts/
│   ├── homework_prompt.py             # day, date, recent_topics, forbidden_hashes
│   ├── review_prompt.py
│   ├── analysis_prompt.py
│   └── feedback_report_prompt.py
├── services/
│   ├── generator.py                   # Daily homework: dedup, generate, save fingerprints
│   ├── review_service.py              # Sunday review — collect wrong Qs from mark_buffer
│   ├── analysis_service.py            # Weekly skills analysis
│   ├── feedback_service.py            # Mark buffer interface + score calculation
│   ├── feedback_report_service.py     # Weekly parent-facing feedback report
│   └── dedup_service.py               # MD5 fingerprint hashing and duplicate check
├── storage/
│   ├── mark_buffer.py                 # In-memory hashmap — single source of truth
│   ├── mark_flusher.py               # Daemon: timestamp-based full overwrite every 5s
│   ├── homework_store.py              # homework.json + analysis.json I/O
│   └── history_store.py               # Directory scanner — no central file
├── pdf/
│   ├── questions_pdf.py               # Questions-only PDF
│   └── answers_pdf.py                # Answers + solution steps PDF
├── ui/
│   ├── app.py                         # Startup: migrate + hydrate + nav + routing
│   ├── components/
│   │   ├── nav.py                     # Horizontal pill navigation bar
│   │   └── question_card.py           # Question display + ✓/✗ marking widget
│   └── pages/
│       ├── today.py                   # Today's homework or Sunday review
│       ├── history.py                 # Browse and mark past days
│       └── progress.py               # Daily scores, topic coverage, weekly reports
└── output/
    ├── raw/YYYY/MM/DD/
    │   ├── homework.json              # Questions, answers, marks, last_update
    │   ├── fingerprints.json          # Dedup hashes for this day
    │   ├── analysis.json              # Sunday only
    │   └── feedback_report.json       # Sunday only
    └── pdf/YYYY/MM/DD/
        ├── questions.pdf
        └── answers.pdf
```

---

## Data Schemas

### `output/raw/YYYY/MM/DD/homework.json`

```json
{
  "day": 5,
  "date": "2026-04-08",
  "session_type": "normal",
  "estimated_minutes": 40,
  "encouragement": "Keep it up!",
  "last_update": "2026-04-08T18:45:00.123",
  "parts": {
    "part1": [
      {
        "id": "p1_001",
        "question": "Calculate 348 × 27",
        "answer": "9396",
        "correct": null,
        "fingerprint": "NBT|multiply|348x27",
        "topic": "5.NBT.B.5"
      }
    ],
    "part2": ["..."],
    "part3": [
      {
        "id": "p3_001",
        "question": "...",
        "answer": "...",
        "correct": null,
        "solution_steps": ["Step 1: ...", "Step 2: ..."],
        "fingerprint": "...",
        "topic": "..."
      }
    ]
  },
  "weekly_challenge": null
}
```

`correct` is `null` (unchecked), `true`, or `false`. Written by the flusher as a full overwrite on every flush.

For Sunday review sessions:

```json
{
  "session_type": "review",
  "reviewed_topics": ["5.NF.A.1"],
  "source_incorrect_count": 3
}
```

### `output/raw/YYYY/MM/DD/fingerprints.json`

```json
["ef9c0e5b...", "217d9ab7...", "..."]
```

MD5 hashes of question fingerprints for this day. Aggregated across all days for dedup on new generation.

---

## How to Run

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set API key. DeepSeek is the default cloud provider.
export DEEPSEEK_API_KEY=...

# Optional, only needed if you choose Gemini in the sidebar
export GEMINI_API_KEY=...

# Optional, only needed if you choose Claude in the sidebar
export ANTHROPIC_API_KEY=sk-ant-...

# Start the app
python -m streamlit run app.py
```

The app will be available at http://localhost:8501.

> If you've already set up the venv, just activate it and run the last two commands.

Localhost runs without the app password by default. Set `AUTH_REQUIRED=true` only if
you want to test the cloud password gate locally.

**Optional — local MLX model:**

Start your MLX OpenAI-compatible inference server at `http://localhost:8080`. Expected endpoint:
```
POST /v1/chat/completions
```
The app auto-detects it and offers it in the sidebar.

---

## AI Providers

| Provider | Details |
|----------|---------|
| **DeepSeek (cloud)** | DeepSeek API — requires `DEEPSEEK_API_KEY`; default model is `deepseek-v4-flash` with thinking `high` |
| **Gemini (cloud)** | Google Gemini API — requires `GEMINI_API_KEY` |
| **Claude (cloud)** | Anthropic API — requires `ANTHROPIC_API_KEY` |
| **Local MLX (Qwen)** | OpenAI-compatible local server at `http://localhost:8080` — no API key needed |

Both implement the same `ModelProvider` abstract interface (`providers/base.py`).

---

## Streamlit Community Cloud Deployment

This deployment is intended for trial use. The app still writes homework,
marks, summaries, and PDFs to the app's local filesystem. That is fine for
testing, but Streamlit Community Cloud runtime files should not be treated as
durable long-term storage. Keep the real long-term record on your local Mac.

### 1. Prepare GitHub

Merge the latest app changes into `main`, then deploy from:

```text
Repository: HaopengLiu-1992/top-math
Branch: main
Main file path: app.py
```

### 2. Create the Streamlit App

1. Open https://share.streamlit.io.
2. Choose **New app**.
3. Select the GitHub repository.
4. Set the branch to `main`.
5. Set the main file path to `app.py`.
6. Open **Advanced settings** before deploying.

### 3. Configure Secrets

Paste this into Streamlit's **Secrets** box:

```toml
AUTH_REQUIRED=true
APP_PASSWORD="choose-a-private-password"

DEEPSEEK_API_KEY="your-deepseek-api-key"

# Optional, only needed if you want Gemini available.
GEMINI_API_KEY="your-gemini-api-key"

# Optional, only needed if you want Claude available.
ANTHROPIC_API_KEY="your-anthropic-api-key"
```

Never commit these values to GitHub. The app reads Streamlit secrets first and
falls back to environment variables for local development.

### 4. Local Secrets Option

For local development, environment variables are enough. If you prefer a local
Streamlit secrets file, create `.streamlit/secrets.toml`:

```toml
DEEPSEEK_API_KEY="your-deepseek-api-key"
GEMINI_API_KEY="your-gemini-api-key"
ANTHROPIC_API_KEY="your-anthropic-api-key"
```

`.streamlit/secrets.toml` is ignored by git.

### 5. Password Behavior

`AUTH_REQUIRED=false` by default, so localhost skips the app password.
Streamlit Cloud should set `AUTH_REQUIRED=true`; if `APP_PASSWORD` is missing,
the app stops before showing homework data.

---

## Curriculum

Follows CCSS Grade 5 math standards, rotating through five domains:

| Domain | Topics |
|--------|--------|
| **5.NBT** | Place value, powers of 10, multi-digit multiplication/division, decimal operations |
| **5.NF** | Add/subtract/multiply/divide fractions and mixed numbers |
| **5.OA** | Order of operations, write expressions, patterns |
| **5.MD** | Unit conversion, line plots, volume |
| **5.G** | Coordinate plane, classify shapes |

Questions require multi-step reasoning and avoid single-digit arithmetic.
