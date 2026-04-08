import os
import time
from datetime import date

import streamlit as st

from providers.anthropic_provider import AnthropicProvider
from providers.mlx_provider import MLXProvider
from services import generator, review_service, generation_tracker
from services.feedback_service import hydrate_marks
from storage import homework_store
from ui.components import question_card


def render(provider_choice: str):
    today = date.today().isoformat()
    is_sunday = review_service.is_sunday()

    st.title(f"{'🔄 Sunday Review' if is_sunday else '📚 Today'} — {today}")

    # ── background generation status ──────────────────────────────────────────
    gen = generation_tracker.get()
    if gen["status"] == "running":
        st.spinner("Generating homework in background...")
        st.info(f"Generating with Claude... you can navigate away and come back.")
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

    # ── metrics ──────────────────────────────────────────────────────────────
    _render_metrics(homework, today, is_sunday)
    st.divider()

    # ── generate button ───────────────────────────────────────────────────────
    if not homework:
        _render_generate_button(today, is_sunday, provider)
    else:
        st.info(f"{'Review' if is_sunday else 'Homework'} already generated for today.")

    # ── content ───────────────────────────────────────────────────────────────
    if homework:
        _render_homework(homework, today, is_sunday)


def _render_metrics(homework, today, is_sunday):
    from services.feedback_service import calc_auto_score
    c1, c2, c3, c4, c5 = st.columns(5)

    if homework:
        c1.metric("Status", "Generated")
        c2.metric("Session", "Review" if is_sunday else f"Day {homework.get('day', '-')}")
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


def _render_generate_button(today, is_sunday, provider):
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
            _run_generate(today, provider)


def _run_generate(today, provider):
    if not _check_api_key(provider):
        return
    generation_tracker.start(today, generator.generate, today, provider)
    st.rerun()


def _run_review(today, provider):
    if not _check_api_key(provider):
        return
    generation_tracker.start(today, review_service.generate_review, today, provider)
    st.rerun()


def _render_homework(homework, today, is_sunday):
    session_type = homework.get("session_type", "normal")
    encouragement = homework.get("encouragement", "")

    if session_type == "review":
        st.markdown(f"**Sunday Review** — {len(homework.get('reviewed_topics', []))} topic(s) revisited")
    else:
        st.markdown(f"*{encouragement}*")

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
    return AnthropicProvider()


def _check_api_key(provider) -> bool:
    if isinstance(provider, AnthropicProvider) and not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY is not set.")
        return False
    return True
