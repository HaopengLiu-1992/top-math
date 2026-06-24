from datetime import date
from html import escape

import streamlit as st

from domain.daily_task import ENGLISH_WRITING
from providers.anthropic_provider import AnthropicProvider
from providers.deepseek_provider import DeepSeekProvider
from providers.gemini_provider import GeminiProvider
from providers.provider_resolver import resolve_provider
from services import feedback_service, writing_service
from settings import secrets
from storage import mark_buffer, writing_store
from ui.components import marking


def render(provider_choice: str):
    today = date.today().isoformat()
    st.markdown(
        f"""
        <div class="tm-module-heading">
            <div>
                <div class="tm-section-label">English writing</div>
                <h2>Writing Memory Set</h2>
                <p>One opinion and three reusable examples for short-response writing.</p>
            </div>
            <span class="tm-chip">{today}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    provider = resolve_provider(provider_choice)
    task = writing_store.load_task(today)

    with st.container(border=True):
        st.markdown('<div class="tm-section-label">Writing setup</div>', unsafe_allow_html=True)
        c1, c2 = st.columns([1, 3])
        grade_level = c1.selectbox("Grade", [5, 6, 7, 8], index=1, key="writing_grade")
        focus = c2.text_input(
            "Focus",
            value="opinion writing for school and academic learning",
            key="writing_focus",
        )

    if not task:
        if st.button("Generate Writing", type="primary", width="stretch", key="writing_generate"):
            _generate(today, provider, grade_level, focus, force=False)
    else:
        st.info("Writing task already generated for today.")
        if st.button("Regenerate Writing", type="secondary", key="writing_regenerate"):
            _generate(today, provider, grade_level, focus, force=True)

    if task:
        feedback_service.hydrate_marks_for(ENGLISH_WRITING, today)
        _render_task(task)
        st.divider()
        _render_pdf_downloads(task)


def _generate(today: str, provider, grade_level: int, focus: str, force: bool):
    if not _check_api_key(provider):
        return
    if force:
        mark_buffer.clear_for(ENGLISH_WRITING, today)
    with st.spinner("Generating writing set..."):
        writing_service.generate(today, provider, grade_level=grade_level, focus=focus, force=force)
    st.rerun()


def _render_task(task: dict):
    examples = task.get("examples", [])
    correct, total = feedback_service.calc_score_for(ENGLISH_WRITING, task["date"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Opinion", "1")
    c2.metric("Examples", len(examples))
    c3.metric("Est. minutes", task.get("estimated_minutes", "—"))
    c4.metric("Marked", f"{correct}/{total}" if total else "—")

    opinion = task.get("opinion", {})
    with st.container(border=True):
        st.markdown('<div class="tm-section-label">Opinion to memorize</div>', unsafe_allow_html=True)
        st.markdown(f"### {opinion.get('memorize_line') or opinion.get('claim', '')}")
        if opinion.get("chinese"):
            st.caption(opinion.get("chinese"))
        if opinion.get("sentence_frame"):
            st.markdown(f"**Frame:** `{opinion.get('sentence_frame')}`")

    st.subheader("Three Examples")
    for idx, item in enumerate(examples, 1):
        with st.container(border=True):
            st.markdown(f"**{idx}. {item.get('memorize_line', '')}**")
            if item.get("chinese"):
                st.caption(item.get("chinese"))
            st.markdown(f"Why it works: {item.get('why_it_works', '')}")
            if item.get("fill_blank"):
                st.markdown(f"Fill blank: {item.get('fill_blank', '')}")

    tab_check, tab_outline = st.tabs(["Recitation Check", "Outline"])
    with tab_check:
        marking.render_score(
            ENGLISH_WRITING,
            task["date"],
            "Mark each sentence after Jessie can say it from memory.",
        )
        _render_memory_mark("opinion", "Opinion", opinion.get("memorize_line") or opinion.get("claim", ""), task["date"])
        for idx, item in enumerate(examples, 1):
            _render_memory_mark(
                item.get("id", f"example_{idx:03d}"),
                f"Example {idx}",
                item.get("memorize_line", ""),
                task["date"],
            )

    with tab_outline:
        for item in task.get("mini_outline", []):
            st.markdown(f"- {item}")
        rewrite = task.get("practice", {}).get("rewrite_task")
        if rewrite:
            st.info(rewrite)


def _render_memory_mark(item_id: str, label: str, line: str, date_str: str):
    with st.container(border=True):
        st.markdown(f"**{escape(label)}**")
        st.markdown(line)
        marking.render_mark(
            ENGLISH_WRITING,
            date_str,
            item_id,
            correct_label="Memorized",
            wrong_label="Needs practice",
        )


def _render_pdf_downloads(task: dict):
    from pdf.writing_pdf import build_answers, build_writing

    date_str = task["date"]
    build_writing(task)
    build_answers(task)
    pdf_d = writing_store.pdf_dir(date_str)
    writing_pdf = pdf_d / "writing.pdf"
    answers_pdf = pdf_d / "answers.pdf"
    c1, c2 = st.columns(2)
    if writing_pdf.exists():
        with open(writing_pdf, "rb") as f:
            c1.download_button("Download Writing PDF", f,
                               file_name=f"writing_{date_str}.pdf",
                               mime="application/pdf", width="stretch")
    if answers_pdf.exists():
        with open(answers_pdf, "rb") as f:
            c2.download_button("Download Answers PDF", f,
                               file_name=f"writing_answers_{date_str}.pdf",
                               mime="application/pdf", width="stretch")


def _check_api_key(provider) -> bool:
    if isinstance(provider, DeepSeekProvider) and not secrets.deepseek_api_key():
        st.error("DEEPSEEK_API_KEY is not set.")
        return False
    if isinstance(provider, AnthropicProvider) and not secrets.anthropic_api_key():
        st.error("ANTHROPIC_API_KEY is not set.")
        return False
    if isinstance(provider, GeminiProvider) and not secrets.gemini_api_key():
        st.error("GEMINI_API_KEY is not set.")
        return False
    return True
