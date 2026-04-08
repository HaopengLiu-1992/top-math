"""
Per-question marking and score calculation.
The mark buffer is the single source of truth — all reads go through it.
"""

from storage import homework_store, history_store, mark_buffer


def hydrate_marks(date_str: str):
    """Load all marks + topics from meta.json into the buffer. Idempotent."""
    meta = homework_store.load_meta(date_str)
    if not meta:
        return
    marks = {qid: data.get("correct") for qid, data in meta.items()}
    mark_buffer.init_date(date_str, marks)


def hydrate_all_marks():
    """Load every logged date into the buffer at startup."""
    for date_str in history_store.get_all_dates():
        hydrate_marks(date_str)


def mark_question(date_str: str, question_id: str, correct: bool):
    """Write mark to buffer. Flusher persists to meta.json every 5s."""
    mark_buffer.set_mark(date_str, question_id, correct)


def calc_auto_score(date_str: str) -> tuple[int, int]:
    """
    Returns (correct_count, total_questions) from buffer only.
    total = all questions (including unchecked / None).
    """
    marks = mark_buffer.get_marks(date_str)
    if not marks:
        return 0, 0
    total = len(marks)
    correct = sum(1 for v in marks.values() if v is True)
    return correct, total
