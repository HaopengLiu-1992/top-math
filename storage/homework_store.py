"""
Per-day file layout under output/raw/YYYY/MM/DD/:

  questions.json    — static content (question text, answers, fingerprints)
                      written once at generation, never updated
  meta.json         — { qid: { correct: null|true|false, topic: "..." } }
                      only file the flusher writes
  analysis.json     — weekly analysis (Sundays only)
  feedback_report.json — weekly feedback report (Sundays only)

output/pdf/YYYY/MM/DD/
  questions.pdf
  answers.pdf
"""

import copy
import json
from pathlib import Path


# ── path helpers ──────────────────────────────────────────────────────────────

def day_dir(date_str: str) -> Path:
    y, m, d = date_str.split("-")
    return Path(f"output/raw/{y}/{m}/{d}")


def questions_path(date_str: str) -> Path:
    return day_dir(date_str) / "questions.json"


def meta_path(date_str: str) -> Path:
    return day_dir(date_str) / "meta.json"


def analysis_path(date_str: str) -> Path:
    return day_dir(date_str) / "analysis.json"


def pdf_dir(date_str: str) -> Path:
    y, m, d = date_str.split("-")
    return Path(f"output/pdf/{y}/{m}/{d}")


# ── questions (static) ────────────────────────────────────────────────────────

def load_questions(date_str: str) -> dict | None:
    p = questions_path(date_str)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def save_questions(hw: dict, date_str: str):
    """Strip correct/topic from each question and write questions.json."""
    data = copy.deepcopy(hw)
    for part in data.get("parts", {}).values():
        for q in part:
            q.pop("correct", None)
            q.pop("topic", None)
    p = questions_path(date_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ── meta (marks + topics) ─────────────────────────────────────────────────────

def load_meta(date_str: str) -> dict:
    """Returns { qid: { correct: null|true|false, topic: str } } or {} if missing."""
    p = meta_path(date_str)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def save_meta(meta: dict, date_str: str):
    p = meta_path(date_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(meta, indent=2, ensure_ascii=False))


def build_meta(hw: dict) -> dict:
    """Build initial meta dict from a freshly generated homework dict."""
    meta = {}
    for part in hw.get("parts", {}).values():
        for q in part:
            meta[q["id"]] = {
                "correct": None,
                "topic": q.get("topic"),
            }
    return meta


# ── analysis ─────────────────────────────────────────────────────────────────

def load_analysis(date_str: str) -> dict | None:
    p = analysis_path(date_str)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def save_analysis(analysis: dict, date_str: str):
    p = analysis_path(date_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(analysis, indent=2))


# ── migration ─────────────────────────────────────────────────────────────────

def migrate_split(date_str: str):
    """Split old homework.json into questions.json + meta.json. Idempotent."""
    old = day_dir(date_str) / "homework.json"
    if not old.exists() or questions_path(date_str).exists():
        return

    hw = json.loads(old.read_text())
    meta = build_meta(hw)
    # Carry over any existing correct values
    for part in hw.get("parts", {}).values():
        for q in part:
            if q["id"] in meta:
                meta[q["id"]]["correct"] = q.get("correct")

    save_questions(hw, date_str)
    save_meta(meta, date_str)
    old.rename(old.parent / "homework.json.migrated")
    print(f"[homework_store] migrated {date_str} → questions.json + meta.json")
