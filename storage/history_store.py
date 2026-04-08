"""
Per-day storage — no central history file.
Scans output/raw/YYYY/MM/DD/ at runtime for questions.json and meta.json.
Scores are never stored — computed live from mark_buffer.
"""

import json
from pathlib import Path
from datetime import date, timedelta

RAW_ROOT = Path("output/raw")


# ── date index ────────────────────────────────────────────────────────────────

def get_all_dates() -> list[str]:
    """Return all homework dates sorted oldest first."""
    dates = []
    for p in RAW_ROOT.glob("*/*/*/questions.json"):
        parts = p.parts  # (..., raw, YYYY, MM, DD, questions.json)
        dates.append(f"{parts[-4]}-{parts[-3]}-{parts[-2]}")
    return sorted(dates)


def get_total_days() -> int:
    """Return the highest day number across all non-review sessions."""
    max_day = 0
    for p in RAW_ROOT.glob("*/*/*/questions.json"):
        try:
            hw = json.loads(p.read_text())
            if hw.get("session_type", "normal") != "review":
                max_day = max(max_day, hw.get("day", 0))
        except Exception:
            pass
    return max_day


# ── fingerprints (dedup) ──────────────────────────────────────────────────────

def load_fingerprints(date_str: str) -> list[str]:
    p = _fp_path(date_str)
    if not p.exists():
        return []
    return json.loads(p.read_text())


def save_fingerprints(date_str: str, hashes: list[str]):
    p = _fp_path(date_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(hashes, indent=2))


def get_all_fingerprints() -> set[str]:
    """Collect fingerprints from all days for dedup."""
    hashes: set[str] = set()
    for p in RAW_ROOT.glob("*/*/*/fingerprints.json"):
        try:
            hashes.update(json.loads(p.read_text()))
        except Exception:
            pass
    return hashes


# ── recent context for prompts ────────────────────────────────────────────────

def get_recent_topics(past_days: int = 14) -> list[str]:
    """Collect unique topics from meta.json files for the past N days."""
    from storage import homework_store
    today = date.today()
    topics: set[str] = set()
    for offset in range(1, past_days + 1):
        meta = homework_store.load_meta((today - timedelta(days=offset)).isoformat())
        for data in meta.values():
            if data.get("topic"):
                topics.add(data["topic"])
    return list(topics)


def get_weekly_logs(date_str: str, past_days: int = 7) -> list[dict]:
    """
    Build log entries for the past N days from questions.json + meta.json + mark_buffer.
    Used by analysis and feedback report prompts.
    """
    from storage import homework_store, mark_buffer
    today = date.fromisoformat(date_str)
    logs = []
    for offset in range(1, past_days + 1):
        d = (today - timedelta(days=offset)).isoformat()
        hw = homework_store.load_questions(d)
        if not hw:
            continue
        meta = homework_store.load_meta(d)
        topics = list({data["topic"] for data in meta.values() if data.get("topic")})
        marks = mark_buffer.get_marks(d)
        total = len(marks)
        correct = sum(1 for v in marks.values() if v is True)
        logs.append({
            "date": d,
            "day": hw.get("day"),
            "session_type": hw.get("session_type", "normal"),
            "topics": topics,
            "auto_score_pct": round(correct / total * 100, 1) if total > 0 else None,
        })
    return sorted(logs, key=lambda x: x["date"])


# ── migration ─────────────────────────────────────────────────────────────────

def migrate_from_old_history():
    """
    One-time migration:
    1. data/history.json fingerprints → per-day fingerprints.json
    2. Each day's homework.json → questions.json + meta.json
    """
    from storage import homework_store

    # Migrate fingerprints from old history.json
    old_path = Path("data/history.json")
    if old_path.exists():
        try:
            data = json.loads(old_path.read_text())
            fps = data.get("fingerprints", [])
            logs = data.get("daily_logs", [])
            idx = 0
            for log in logs:
                count = log.get("fingerprint_count", 0)
                day_fps = fps[idx: idx + count]
                idx += count
                date_str = log.get("date")
                if date_str and day_fps:
                    fp_p = _fp_path(date_str)
                    if not fp_p.exists():
                        fp_p.parent.mkdir(parents=True, exist_ok=True)
                        fp_p.write_text(json.dumps(day_fps, indent=2))
            old_path.rename(old_path.parent / "history.json.migrated")
            print("[history_store] migrated data/history.json → per-day fingerprints.json")
        except Exception as e:
            print(f"[history_store] fingerprint migration failed: {e}")

    # Migrate each day's homework.json → questions.json + meta.json
    for p in sorted(RAW_ROOT.glob("*/*/*/homework.json")):
        parts = p.parts
        date_str = f"{parts[-4]}-{parts[-3]}-{parts[-2]}"
        homework_store.migrate_split(date_str)


# ── internal ──────────────────────────────────────────────────────────────────

def _fp_path(date_str: str) -> Path:
    y, m, d = date_str.split("-")
    return RAW_ROOT / y / m / d / "fingerprints.json"
