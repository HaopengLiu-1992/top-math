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
            visual = q.get("visual")
            if visual:
                st.code(visual.get("plain_text", ""), language="text")
        st.markdown("")

    challenge = homework.get("weekly_challenge")
    if challenge:
        st.divider()
        st.markdown("**Weekly Challenge (Optional Bonus)**")
        st.markdown(challenge["question"])


def render_lesson_tab(homework: dict):
    lesson = homework.get("lesson")
    if not lesson:
        st.info("No lesson was generated for this session.")
        return

    st.subheader(lesson.get("title", "Lesson"))
    plain_text = lesson.get("plain_text")
    if plain_text:
        st.text(plain_text)
        return

    objective = lesson.get("objective")
    if objective:
        st.markdown(f"**Objective:** {objective}")

    explanation = lesson.get("concept_explanation")
    if explanation:
        st.markdown(explanation)

    examples = lesson.get("worked_examples", [])
    if examples:
        st.markdown("**Worked examples**")
        for example in examples:
            with st.expander(example.get("problem", "Example"), expanded=True):
                for step in example.get("steps", []):
                    st.markdown(f"- {step}")
                note = example.get("teaching_note")
                if note:
                    st.caption(note)

    mistakes = lesson.get("common_mistakes", [])
    if mistakes:
        st.markdown("**Common mistakes**")
        for item in mistakes:
            mistake = item.get("mistake", "")
            fix = item.get("fix", "")
            why = item.get("why_it_happens", "")
            with st.expander(mistake or "Mistake"):
                if why:
                    st.markdown(f"**Why it happens:** {why}")
                if fix:
                    st.markdown(f"**Fix:** {fix}")

    checks = lesson.get("try_this_first", [])
    if checks:
        st.markdown("**Try this first**")
        for prompt in checks:
            st.markdown(f"- {prompt}")


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
        visual = q.get("visual")
        if visual:
            st.code(visual.get("plain_text", ""), language="text")
        hint = q.get("hint")
        if hint:
            with st.expander("Hint"):
                st.markdown(hint)
        st.markdown(f"**Answer:** {q['answer']}")
        teaching_point = q.get("teaching_point")
        if teaching_point:
            st.caption(teaching_point)
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
