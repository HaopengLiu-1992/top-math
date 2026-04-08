import streamlit as st
from services import feedback_service
from storage.mark_buffer import get_marks

PART_LABELS = {
    "part1": "Part 1 — Warm-up",
    "part2": "Part 2 — Core Focus",
    "part3": "Part 3 — Word Problems",
}


def render_questions_tab(homework: dict):
    parts = homework.get("parts", {})
    for part_key, label in PART_LABELS.items():
        questions = parts.get(part_key, [])
        if not questions:
            continue
        st.markdown(f"**{label}**")
        for i, q in enumerate(questions, 1):
            st.markdown(f"{i}. {q['question']}")
        st.markdown("")

    challenge = homework.get("weekly_challenge")
    if challenge:
        st.divider()
        st.markdown("**Weekly Challenge (Optional Bonus)**")
        st.markdown(challenge["question"])


def render_answers_tab(homework: dict, date_str: str, allow_marking: bool = True):
    if allow_marking:
        correct, total = feedback_service.calc_auto_score(date_str)
        if total > 0:
            st.progress(correct / total,
                        text=f"Marked: {correct}/{total} correct ({correct/total*100:.0f}%)")
        else:
            st.info("Mark each question ✓ or ✗ after checking the answer.")
        st.markdown("")

    parts = homework.get("parts", {})
    for part_key, label in PART_LABELS.items():
        questions = parts.get(part_key, [])
        if not questions:
            continue
        st.markdown(f"**{label}**")
        for i, q in enumerate(questions, 1):
            _render_question_card(q, i, date_str, allow_marking)
        st.markdown("")

    challenge = homework.get("weekly_challenge")
    if challenge:
        st.divider()
        st.markdown("**Weekly Challenge**")
        with st.expander(challenge["question"]):
            st.markdown(f"**Answer:** {challenge['answer']}")
            for step in challenge.get("solution_steps", []):
                st.markdown(f"- {step}")


def _render_question_card(q: dict, index: int, date_str: str, allow_marking: bool):
    # Buffer is the single source of truth — all state read from hashmap
    marks = get_marks(date_str)
    correct = marks.get(q["id"])  # True / False / None (unchecked)

    with st.container(border=True):
        st.markdown(f"**{index}. {q['question']}**")
        st.markdown(f"**Answer:** {q['answer']}")
        for step in q.get("solution_steps", []):
            st.markdown(f"- {step}")

        if allow_marking:
            c_status, c_radio = st.columns([2, 4])

            if correct is True:
                c_status.markdown(
                    '<span style="background:#1a7f37;color:white;padding:4px 12px;'
                    'border-radius:6px;font-weight:600">✓ Correct</span>',
                    unsafe_allow_html=True,
                )
            elif correct is False:
                c_status.markdown(
                    '<span style="background:#c0392b;color:white;padding:4px 12px;'
                    'border-radius:6px;font-weight:600">✗ Wrong</span>',
                    unsafe_allow_html=True,
                )

            options = ["✓ Correct", "✗ Wrong"]
            current = "✓ Correct" if correct is True else ("✗ Wrong" if correct is False else None)
            choice = c_radio.radio(
                "Result",
                options,
                index=options.index(current) if current else None,
                key=f"mark_{date_str}_{q['id']}",
                horizontal=True,
                label_visibility="collapsed",
            )
            if choice and choice != current:
                feedback_service.mark_question(date_str, q["id"], choice == "✓ Correct")
                st.rerun()
