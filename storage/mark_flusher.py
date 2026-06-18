"""
Background daemon thread — wakes every 5 seconds.
Scans mark_buffer: dates with last_update within past 5s → dump to meta.json.
Only meta.json is written — questions.json is never touched after generation.
"""

import threading
import time
import logging

from domain.daily_task import MATH_HOMEWORK, TaskScope
from storage import daily_task_store, homework_store, mark_buffer

logger = logging.getLogger(__name__)

_FLUSH_INTERVAL = 5
_started = False
_start_lock = threading.Lock()


def start():
    global _started
    with _start_lock:
        if _started:
            return
        t = threading.Thread(target=_run, daemon=True, name="mark-flusher")
        t.start()
        _started = True
        logger.info("Mark flusher started (interval=%ds)", _FLUSH_INTERVAL)


def _run():
    while True:
        time.sleep(_FLUSH_INTERVAL)
        _flush()


def _flush():
    for scope, date_str, marks, last_update in mark_buffer.get_recently_updated(_FLUSH_INTERVAL):
        try:
            _write_meta(scope, date_str, marks)
        except Exception:
            logger.exception("Failed to flush marks for %s/%s", scope.key, date_str)


def _write_meta(scope: TaskScope, date_str: str, marks: dict):
    """Full overwrite of meta.json with current marks from buffer."""
    meta = homework_store.load_meta(date_str) if scope == MATH_HOMEWORK else daily_task_store.load_meta(scope, date_str)
    if not meta:
        return

    for qid, data in meta.items():
        if qid in marks:
            data["correct"] = marks[qid]
            if "known" in data:
                data["known"] = marks[qid]

    if scope == MATH_HOMEWORK:
        homework_store.save_meta(meta, date_str)
    else:
        daily_task_store.save_meta(scope, date_str, meta)
    logger.debug("Flushed meta for %s/%s", scope.key, date_str)
