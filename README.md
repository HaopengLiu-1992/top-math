# Daily Learning Generator

A Streamlit app that generates daily math, vocabulary, English reading, English
writing, and science reading practice for Jessie. It uses scoped daily tasks so multiple
subjects can share providers, storage, PDFs, history, and analysis.

## Features

- Daily Grade 5-8 math homework following CCSS standards — one generation per day (idempotent/cached)
- Daily math/science academic vocabulary practice — 20 words from a 10,000-word academic candidate bank
- Daily English reading practice — passage, vocabulary, comprehension, inference, and short response
- Daily English writing practice — one reusable opinion and three memorized examples
- Daily science reading practice — science passage, academic vocabulary, evidence/cause-effect questions
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
│  Daily · History · Analysis                               │
└────────┼───────────────┼─────────────────────┼────────────┘
         │               │                     │
┌────────▼───────────────▼─────────────────────▼────────────┐
│                        Services                           │
│  generator · vocabulary_service · reading_service         │
│  writing_service · analysis_service · summary_service     │
│  feedback_service · feedback_report_service · dedup       │
└──────────────┬────────────────────────────────────────────┘
               │
    ┌──────────▼──────────────────────────────────────────┐
    │                     Storage                         │
    │                                                     │
    │  daily_task_store(subject, task_type, date)          │
    │      │                                              │
    │  homework_store / vocabulary_store / reading_store  │
    │  writing_store                                      │
    │      │                                              │
    │  scoped mark_buffer ◄── single source of mark truth │
    │      │                                              │
    │  mark_flusher (daemon, 5s timestamp-based flush)    │
    └──────────────────────────┬──────────────────────────┘
                               │
              ┌────────────────┼───────────────┐
              ▼                ▼               ▼
         Providers           PDF           output/tasks/
       DeepSeek/Gemini   questions         subject/task_type/
       Claude/MLX        answers           raw + pdf
```

---

## Scoped Daily Tasks

The app is now organized around a scoped daily task:

```
TaskScope(subject="math", task_type="homework")
TaskScope(subject="english", task_type="vocabulary")
TaskScope(subject="english", task_type="reading")
TaskScope(subject="english", task_type="writing")
TaskScope(subject="science", task_type="reading")
```

That scope is part of storage, marks, PDFs, and history lookup. This prevents
same-day work from different subjects from colliding.

```
output/tasks/<subject>/<task_type>/
├── raw/YYYY/MM/DD/task.json
├── raw/YYYY/MM/DD/meta.json
├── raw/YYYY/MM/DD/fingerprints.json
└── pdf/YYYY/MM/DD/
    ├── questions.pdf      # math
    ├── vocabulary.pdf     # vocabulary
    ├── reading.pdf        # reading
    ├── writing.pdf        # writing
    └── answers.pdf
```

Current task scopes:

| Scope | UI | Generator | Store facade | PDF |
|-------|----|-----------|--------------|-----|
| `math/homework` | Today | `services.generator` | `homework_store` | `questions_pdf`, `answers_pdf` |
| `english/vocabulary` | Vocabulary | `vocabulary_service` | `vocabulary_store` | `vocabulary_pdf` |
| `english/reading` | Daily / English Reading | `reading_service` | `reading_store` | `reading_pdf` |
| `english/writing` | Daily / English Writing | `writing_service` | `writing_store` | `writing_pdf` |
| `science/reading` | Daily / Science Reading | `reading_service` | `reading_store` | `reading_pdf` |

The top-level UI intentionally stays small:

- **Daily**: command-center overview cards plus a task switcher for Math, Vocabulary, English Reading, English Writing, and Science Reading
- **History**: all generated tasks across all scopes
- **Analysis**: cross-subject activity overview plus math-specific score/topic analysis

---

## Mark Buffer — Single Source of Truth

All mark state lives in one in-memory hashmap keyed by scope and date. The UI
reads marks from the buffer; the background flusher persists changed entries to
the matching scoped `meta.json`.

```
mark_buffer._store = {
  "math/homework/2026-04-06": {
    "scope": TaskScope("math", "homework"),
    "date_str": "2026-04-06",
    "marks": {"p1_001": True, "p1_002": False, "p1_003": None},
    "last_update": "2026-04-06T18:30:00.123"
  },
  "english/vocabulary/2026-04-06": {
    "scope": TaskScope("english", "vocabulary"),
    "date_str": "2026-04-06",
    "marks": {"quotient": True, "estimate": None},
    "last_update": ""
  }
}
```

Compatibility wrappers keep existing math calls working:

```
mark_buffer.get_marks(date)      # defaults to math/homework
mark_buffer.get_marks_for(scope, date)
```

---

## Legacy Math Compatibility

New math homework writes to the scoped task tree. Existing historical homework
is still readable from the old layout:

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

`homework_store` is now a compatibility facade:

- `load_questions(date)` reads `output/tasks/math/homework/...` first, then the legacy `output/raw/...`
- `save_questions(date)` writes the scoped task and legacy questions file during the transition
- `load_meta(date)` / `save_meta(date)` do the same for marks
- `pdf_dir(date)` points to the new scoped PDF directory
- History PDF downloads fall back to the old `output/pdf/...` directory when needed

`history_store` scans both the new math task tree and legacy tree:

- `get_all_dates()` → scoped math tasks plus legacy `questions.json`
- `get_total_days()` → max `day` field across non-review sessions
- `get_all_fingerprints()` → union of all per-day `fingerprints.json`
- `get_recent_topics(14)` → topics from scoped or legacy meta
- `get_weekly_logs(date, 7)` → log entries built from homework + scoped mark buffer scores

**Scores are never stored** — always computed live from mark_buffer.

---

## Vocabulary Bank

Vocabulary practice uses `config/vocabulary/academic_word_bank_10000.json`.
The bank contains:

- 275 curated math/science/academic core words ordered from middle-school basics
- 10,000 ranked academic candidates drawn from the local English word list
- `cn_stage` mapping such as `cn_middle_school`, `cn_high_school`, and extension levels
- `us_band` mapping such as `us_grade_5_8`, `us_grade_8_10`, and `us_grade_10_12`
- categories for math operations, word-problem signals, geometry, science process, and general academic vocabulary

The model fills any missing Chinese/definition fields at generation time and
keeps examples tied to math/science reading where possible.

Runtime selection does **not** send the 10,000-word bank to the model. The app
uses `config/vocabulary/vocabulary_index.json` to pick the next 15 new words and
5 review words locally, starting from curated middle-school math/science basics.
Only those selected daily words are included in the LLM prompt. The selector also
filters fallback candidates so unvetted dictionary words are not used for daily
practice. Regenerating a date ignores that date's previous vocabulary meta so
bad output can be replaced cleanly.

---

## Reading Guardrail Sidecar

Reading generation uses a low-intrusion sidecar to reduce repeated Grade 5-8
passages without growing the prompt over time.

`services.reading_guardrail` adds three steps around the existing
`reading_service.generate()` flow:

1. `prepare(scope, date, grade, focus)` selects a slot:
   grade, domain, topic, subtopic, text type, and target skill.
2. `validate(scope, task, plan)` checks structure, rough grade-level length,
   required vocabulary/question counts, evidence/detail coverage, and concept
   similarity.
3. `commit(scope, date, task, plan)` stores long-term concept memory.

The prompt receives only:

- the current slot
- the selected core concept
- a small top-k list of similar concepts to avoid

It does **not** receive the full reading history. Concept memory is stored in:

```
output/reading_guardrail/concepts.json
```

Each committed record includes concept, deterministic embedding, metadata, and
an `external_passage_id`. The embedding implementation is local and deterministic
today, so the sidecar has no extra API cost; it can be swapped for a hosted
embedding provider later without changing the reading UI.

---

## Layer Responsibilities

| Layer | Path | Responsibility |
|-------|------|----------------|
| **UI** | `ui/pages/`, `ui/components/` | Streamlit pages and marking widgets |
| **Services** | `services/` | Business logic — generation, dedup, scoring, review |
| **Providers** | `providers/` | AI model abstraction (DeepSeek API / Claude API / Gemini API / local MLX) |
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
