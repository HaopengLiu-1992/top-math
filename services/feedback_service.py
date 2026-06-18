"""
Per-question marking and score calculation.
The mark buffer is the single source of truth — all reads go through it.
"""

from domain.daily_task import MATH_HOMEWORK, TaskScope
from storage import daily_task_store, homework_store, history_store, mark_buffer


def hydrate_marks(date_str: str):
    """Load all marks + topics from meta.json into the buffer. Idempotent."""
    hydrate_marks_for(MATH_HOMEWORK, date_str)


def hydrate_marks_for(scope: TaskScope, date_str: str):
    """Load scoped marks from meta.json into the buffer. Idempotent."""
    meta = homework_store.load_meta(date_str) if scope == MATH_HOMEWORK else daily_task_store.load_meta(scope, date_str)
    if not meta:
        return
    marks = {
        qid: data.get("correct", data.get("known"))
        for qid, data in meta.items()
    }
    mark_buffer.init_for(scope, date_str, marks)


def hydrate_all_marks():
    """Load every logged date into the buffer at startup."""
    for date_str in history_store.get_all_dates():
        hydrate_marks(date_str)


def mark_question(date_str: str, question_id: str, correct: bool):
    """Write mark to buffer. Flusher persists to meta.json every 5s."""
    mark_item_for(MATH_HOMEWORK, date_str, question_id, correct)


def mark_item_for(scope: TaskScope, date_str: str, item_id: str, correct: bool):
    """Write a scoped mark to buffer. Flusher persists to meta.json every 5s."""
    mark_buffer.set_mark_for(scope, date_str, item_id, correct)


def calc_auto_score(date_str: str) -> tuple[int, int]:
    """
    Returns (correct_count, total_questions) from buffer only.
    total = all questions (including unchecked / None).
    """
    return calc_score_for(MATH_HOMEWORK, date_str)


def calc_score_for(scope: TaskScope, date_str: str) -> tuple[int, int]:
    """Returns (correct_count, total_items) for any scoped daily task."""
    marks = mark_buffer.get_marks_for(scope, date_str)
    if not marks:
        return 0, 0
    total = len(marks)
    correct = sum(1 for v in marks.values() if v is True)
    return correct, total
