import os
import time
from datetime import date

import streamlit as st

from providers.anthropic_provider import AnthropicProvider
from providers.gemini_provider import GeminiProvider
from providers.mlx_provider import MLXProvider
from services import curriculum_service
from services import generator, review_service, generation_tracker
from services.feedback_service import hydrate_marks
from storage import homework_store, mark_buffer, history_store
from ui.components import question_card


def render(provider_choice: str):
    today = date.today().isoformat()
    is_sunday = review_service.is_sunday()

    st.title(f"{'🔄 Sunday Review' if is_sunday else '📚 Today'} — {today}")

    # ── background generation status ──────────────────────────────────────────
    gen = generation_tracker.get()
    if gen["status"] == "running":
        st.spinner("Generating homework in background...")
        provider_name = gen.get("provider_name") or "selected provider"
        st.info(f"Generating with {provider_name}... you can navigate away and come back.")
        time.sleep(2)
        st.rerun()
        return
    if gen["status"] == "done":
        hydrate_marks(gen["date_str"])
        generation_tracker.reset()
        st.rerun()
        return
    if gen["status"] == "error":
        st.error(f"Generation failed: {gen['error']}")
        generation_tracker.reset()

    homework = homework_store.load_questions(today)
    provider = _resolve_provider(provider_choice)
    course_options = _render_course_controls(homework)

    # ── metrics ──────────────────────────────────────────────────────────────
    _render_metrics(homework, today, is_sunday)
    st.divider()

    # ── generate / regenerate button ──────────────────────────────────────────
    if not homework:
        _render_generate_button(today, is_sunday, provider, course_options)
    else:
        st.info(f"{'Review' if is_sunday else 'Homework'} already generated for today.")
        _render_regenerate_button(today, is_sunday, provider, course_options)

    # ── content ───────────────────────────────────────────────────────────────
    if homework:
        _render_homework(homework, today, is_sunday)


def _render_metrics(homework, today, is_sunday):
    from services.feedback_service import calc_auto_score
    c1, c2, c3, c4, c5 = st.columns(5)

    if homework:
        c1.metric("Status", "Generated")
        grade = homework.get("grade_level", 6)
        session = "Review" if is_sunday else f"Grade {grade} · Day {homework.get('day', '-')}"
        c2.metric("Session", session)
        c3.metric("Est. minutes", homework.get("estimated_minutes", "—"))
        correct, total = calc_auto_score(today)
        c4.metric("Marked", f"{correct}/{total}" if total else "—")
        c5.metric("Model", homework.get("model", "—"))
    else:
        c1.metric("Status", "Not generated")
        c2.metric("Session", "Sunday Review" if is_sunday else "Normal")
        c3.metric("Est. minutes", "~40")
        c4.metric("Marked", "—")
        c5.metric("Model", "—")


def _render_course_controls(homework):
    st.subheader("Course")
    current_grade = int(homework.get("grade_level", 6)) if homework else 6
    current_mode = (homework or {}).get("mode", "lesson_practice")
    mode_options = ["Lesson + Practice", "Practice Only", "Challenge"]
    mode_by_value = {
        "lesson_practice": "Lesson + Practice",
        "practice_only": "Practice Only",
        "challenge": "Challenge",
    }
    current_mode_label = mode_by_value.get(current_mode, "Lesson + Practice")
    grades = [5, 6, 7, 8]
    c1, c2, c3 = st.columns([1, 2, 2])
    grade_level = c1.selectbox(
        "Grade",
        grades,
        index=grades.index(current_grade) if current_grade in grades else 1,
    )
    mode_label = c2.selectbox(
        "Mode",
        mode_options,
        index=mode_options.index(current_mode_label),
    )
    include_lesson = c3.checkbox(
        "Include lesson",
        value=bool((homework or {}).get("lesson")) or mode_label == "Lesson + Practice",
        disabled=mode_label == "Practice Only",
    )

    topics = curriculum_service.list_topics("math", grade_level)
    topic_options = [None] + [t.id for t in topics]
    topic_labels = {None: "Auto"}
    topic_labels.update({t.id: f"{t.id} — {t.title}" for t in topics})
    existing_topic_id = (homework or {}).get("target_topic", {}).get("id")
    selected_topic = st.selectbox(
        "Topic",
        topic_options,
        index=topic_options.index(existing_topic_id) if existing_topic_id in topic_options else 0,
        format_func=lambda value: topic_labels[value],
    )
    include_hints = st.checkbox("Include hints", value=True)

    mode_map = {
        "Lesson + Practice": "lesson_practice",
        "Practice Only": "practice_only",
        "Challenge": "challenge",
    }
    return {
        "grade_level": grade_level,
        "mode": mode_map[mode_label],
        "include_lesson": include_lesson,
        "include_hints": include_hints,
        "target_topic_id": selected_topic,
    }


def _render_generate_button(today, is_sunday, provider, course_options):
    if is_sunday:
        incorrect = review_service.collect_incorrect_questions(today)
        if not incorrect:
            st.balloons()
            st.success("No mistakes this week — great job! No review needed. Enjoy your Sunday!")
            return

        st.warning(f"{len(incorrect)} incorrect question(s) from this week. Generating review...")
        if st.button("Generate Sunday Review", type="primary", width="stretch"):
            _run_review(today, provider)
    else:
        if st.button("Generate Today's Homework", type="primary", width="stretch"):
            _run_generate(today, provider, course_options)


def _run_generate(today, provider, course_options):
    if not _check_api_key(provider):
        return
    generation_tracker.start(today, generator.generate, today, provider, **course_options)
    st.rerun()


def _run_review(today, provider):
    if not _check_api_key(provider):
        return
    generation_tracker.start(today, review_service.generate_review, today, provider)
    st.rerun()


def _render_regenerate_button(today, is_sunday, provider, course_options):
    if st.button("Regenerate Today's Homework", type="secondary"):
        st.session_state["confirm_regen"] = True

    if st.session_state.get("confirm_regen"):
        st.warning("This will delete today's homework and all marks. Continue?")
        c1, c2 = st.columns(2)
        if c1.button("Yes, regenerate", type="primary", width="stretch"):
            _do_regenerate(today, is_sunday, provider, course_options)
        if c2.button("Cancel", width="stretch"):
            st.session_state.pop("confirm_regen", None)
            st.rerun()


def _do_regenerate(today, is_sunday, provider, course_options):
    if not _check_api_key(provider):
        return
    mark_buffer.clear_date(today)
    homework_store.delete_for_date(today)
    history_store.delete_fingerprints(today)
    st.session_state.pop("confirm_regen", None)
    if is_sunday:
        generation_tracker.start(today, review_service.generate_review, today, provider)
    else:
        generation_tracker.start(today, generator.generate, today, provider, **course_options)
    st.rerun()


def _render_homework(homework, today, is_sunday):
    session_type = homework.get("session_type", "normal")
    encouragement = homework.get("encouragement", "")

    if session_type == "review":
        st.markdown(f"**Sunday Review** — {len(homework.get('reviewed_topics', []))} topic(s) revisited")
    else:
        st.markdown(f"*{encouragement}*")

    if homework.get("lesson"):
        tab_l, tab_q, tab_a = st.tabs(["Lesson", "Questions", "Answers"])
        with tab_l:
            question_card.render_lesson_tab(homework)
    else:
        tab_q, tab_a = st.tabs(["Questions", "Answers"])

    with tab_q:
        question_card.render_questions_tab(homework)

    with tab_a:
        question_card.render_answers_tab(homework, today, allow_marking=True)

    st.divider()
    _render_pdf_downloads(today)


def _render_pdf_downloads(date_str):
    pdf_d = homework_store.pdf_dir(date_str)
    q_pdf = pdf_d / "questions.pdf"
    a_pdf = pdf_d / "answers.pdf"

    c1, c2 = st.columns(2)
    if q_pdf.exists():
        with open(q_pdf, "rb") as f:
            c1.download_button("Download Questions PDF", f,
                               file_name=f"questions_{date_str}.pdf",
                               mime="application/pdf", width="stretch")
    if a_pdf.exists():
        with open(a_pdf, "rb") as f:
            c2.download_button("Download Answers PDF", f,
                               file_name=f"answers_{date_str}.pdf",
                               mime="application/pdf", width="stretch")


def _resolve_provider(choice: str):
    if choice.startswith("Local"):
        return MLXProvider()
    if choice.startswith("Gemini"):
        return GeminiProvider()
    return AnthropicProvider()


def _check_api_key(provider) -> bool:
    if isinstance(provider, AnthropicProvider) and not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY is not set.")
        return False
    if isinstance(provider, GeminiProvider) and not os.environ.get("GEMINI_API_KEY"):
        st.error("GEMINI_API_KEY is not set.")
        return False
    return True
