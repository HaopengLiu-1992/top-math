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

from domain.daily_task import MATH_HOMEWORK, TaskScope

_lock = threading.Lock()
_store: dict[str, dict] = {}


def _scope_key(scope: TaskScope, date_str: str) -> str:
    return f"{scope.key}/{date_str}"


def init_date(date_str: str, marks: dict[str, bool | None]):
    init_for(MATH_HOMEWORK, date_str, marks)


def init_for(scope: TaskScope, date_str: str, marks: dict[str, bool | None]):
    """Load a date from disk. last_update is blank — not dirty, no flush needed."""
    key = _scope_key(scope, date_str)
    with _lock:
        if key not in _store:
            _store[key] = {
                "scope": scope,
                "date_str": date_str,
                "marks": dict(marks),
                "last_update": "",  # not dirty
            }


def set_mark(date_str: str, qid: str, correct: bool):
    set_mark_for(MATH_HOMEWORK, date_str, qid, correct)


def set_mark_for(scope: TaskScope, date_str: str, qid: str, correct: bool):
    """Update a mark. Sets last_update to now so flusher picks it up."""
    key = _scope_key(scope, date_str)
    with _lock:
        if key not in _store:
            _store[key] = {"scope": scope, "date_str": date_str, "marks": {}, "last_update": ""}
        _store[key]["marks"][qid] = correct
        _store[key]["last_update"] = datetime.now().isoformat()


def get_marks(date_str: str) -> dict[str, bool | None]:
    return get_marks_for(MATH_HOMEWORK, date_str)


def get_marks_for(scope: TaskScope, date_str: str) -> dict[str, bool | None]:
    """Return a snapshot of all marks for a date."""
    key = _scope_key(scope, date_str)
    with _lock:
        entry = _store.get(key)
        return dict(entry["marks"]) if entry else {}


def clear_date(date_str: str):
    clear_for(MATH_HOMEWORK, date_str)


def clear_for(scope: TaskScope, date_str: str):
    """Remove a date from the buffer entirely (used before regeneration)."""
    key = _scope_key(scope, date_str)
    with _lock:
        _store.pop(key, None)


def get_recently_updated(within_seconds: int) -> list[tuple[TaskScope, str, dict, str]]:
    """
    Return dates whose last_update falls within the past N seconds.
    Used by the flusher to decide what to dump.
    """
    cutoff = datetime.now() - timedelta(seconds=within_seconds)
    with _lock:
        result = []
        for entry in _store.values():
            lu = entry.get("last_update", "")
            if lu and datetime.fromisoformat(lu) > cutoff:
                result.append((entry["scope"], entry["date_str"], dict(entry["marks"]), lu))
        return result
