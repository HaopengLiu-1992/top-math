"""
Single source of truth for all question marks across all dates.

Structure:
  _store = {
    "yyyy-mm-dd": {
      "marks":       { question_id: True | False | None },
      "last_update": "2026-04-06T18:30:00.123"   ← "" means loaded from disk, not dirty
    },
    ...
  }

Flusher checks last_update on each tick: if within the last 5s → dump to disk.
"""

import threading
from datetime import datetime, timedelta

_lock = threading.Lock()
_store: dict[str, dict] = {}


def init_date(date_str: str, marks: dict[str, bool | None]):
    """Load a date from disk. last_update is blank — not dirty, no flush needed."""
    with _lock:
        if date_str not in _store:
            _store[date_str] = {
                "marks": dict(marks),
                "last_update": "",  # not dirty
            }


def set_mark(date_str: str, qid: str, correct: bool):
    """Update a mark. Sets last_update to now so flusher picks it up."""
    with _lock:
        if date_str not in _store:
            _store[date_str] = {"marks": {}, "last_update": ""}
        _store[date_str]["marks"][qid] = correct
        _store[date_str]["last_update"] = datetime.now().isoformat()


def get_marks(date_str: str) -> dict[str, bool | None]:
    """Return a snapshot of all marks for a date."""
    with _lock:
        entry = _store.get(date_str)
        return dict(entry["marks"]) if entry else {}


def get_recently_updated(within_seconds: int) -> list[tuple[str, dict, str]]:
    """
    Return dates whose last_update falls within the past N seconds.
    Used by the flusher to decide what to dump.
    """
    cutoff = datetime.now() - timedelta(seconds=within_seconds)
    with _lock:
        result = []
        for date_str, entry in _store.items():
            lu = entry.get("last_update", "")
            if lu and datetime.fromisoformat(lu) > cutoff:
                result.append((date_str, dict(entry["marks"]), lu))
        return result
