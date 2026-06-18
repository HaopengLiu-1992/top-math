import streamlit as st

from domain.daily_task import TaskScope
from services import feedback_service
from storage import mark_buffer


def render_score(scope: TaskScope, date_str: str, empty_text: str):
    correct, total = feedback_service.calc_score_for(scope, date_str)
    if total > 0:
        st.progress(
            correct / total,
            text=f"Marked: {correct}/{total} correct ({correct / total * 100:.0f}%)",
        )
    else:
        st.info(empty_text)


def render_mark(scope: TaskScope, date_str: str, item_id: str,
                correct_label: str = "Correct", wrong_label: str = "Wrong"):
    marks = mark_buffer.get_marks_for(scope, date_str)
    current_value = marks.get(item_id)
    options = [f"✓ {correct_label}", f"✗ {wrong_label}"]
    current = (
        options[0] if current_value is True
        else options[1] if current_value is False
        else None
    )
    choice = st.radio(
        "Result",
        options,
        index=options.index(current) if current else None,
        key=f"mark_{scope.key}_{date_str}_{item_id}",
        horizontal=True,
        label_visibility="collapsed",
    )
    if choice and choice != current:
        feedback_service.mark_item_for(scope, date_str, item_id, choice == options[0])
        st.rerun()
