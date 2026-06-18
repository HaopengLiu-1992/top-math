from datetime import date

import streamlit as st

from domain.daily_task import ENGLISH_READING, SCIENCE_READING, TASK_LABELS, TaskScope
from providers.anthropic_provider import AnthropicProvider
from providers.deepseek_provider import DeepSeekProvider
from providers.gemini_provider import GeminiProvider
from providers.provider_resolver import resolve_provider
from services import reading_service
from settings import secrets
from storage import reading_store


def render(scope: TaskScope, provider_choice: str):
    today = date.today().isoformat()
    label = TASK_LABELS[scope]
    provider = resolve_provider(provider_choice)
    task = reading_store.load_task(scope, today)

    st.subheader(label)
    with st.container(border=True):
        c1, c2 = st.columns([1, 3])
        grade_level = c1.selectbox(
            f"{label} Grade",
            [5, 6, 7, 8],
            index=1,
            key=f"{scope.key}_grade",
        )
        focus = c2.text_input(
            f"{label} Focus",
            value=reading_service.default_focus(scope),
            key=f"{scope.key}_focus",
        )

    if not task:
        if st.button(f"Generate {label}", type="primary", width="stretch", key=f"{scope.key}_generate"):
            _generate(scope, today, provider, grade_level, focus, force=False)
    else:
        st.info(f"{label} already generated for today.")
        if st.button(f"Regenerate {label}", type="secondary", key=f"{scope.key}_regenerate"):
            _generate(scope, today, provider, grade_level, focus, force=True)

    if task:
        _render_task(task)
        st.divider()
        _render_pdf_downloads(scope, today)


def _generate(scope: TaskScope, today: str, provider, grade_level: int, focus: str, force: bool):
    if not _check_api_key(provider):
        return
    with st.spinner("Generating reading task..."):
        reading_service.generate(scope, today, provider, grade_level=grade_level, focus=focus, force=force)
    st.rerun()


def _render_task(task: dict):
    passage = task.get("passage", {})
    questions = task.get("questions", [])
    vocab = task.get("vocabulary", [])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Words", passage.get("word_count", "—"))
    c2.metric("Vocabulary", len(vocab))
    c3.metric("Questions", len(questions))
    c4.metric("Model", task.get("model", "—"))

    st.markdown(f"### {passage.get('title', 'Passage')}")
    st.write(passage.get("text", ""))

    tab_v, tab_q, tab_a = st.tabs(["Vocabulary", "Questions", "Answers"])
    with tab_v:
        for item in vocab:
            st.markdown(f"- **{item.get('word', '')}** ({item.get('chinese', '')}) — {item.get('definition', '')}")
            st.caption(item.get("sentence", ""))
    with tab_q:
        for idx, item in enumerate(questions, 1):
            st.markdown(f"{idx}. {item.get('question', '')}")
    with tab_a:
        for idx, item in enumerate(questions, 1):
            st.markdown(f"{idx}. **{item.get('answer', '')}**")


def _render_pdf_downloads(scope: TaskScope, date_str: str):
    pdf_d = reading_store.pdf_dir(scope, date_str)
    reading_pdf = pdf_d / "reading.pdf"
    answers_pdf = pdf_d / "answers.pdf"
    c1, c2 = st.columns(2)
    if reading_pdf.exists():
        with open(reading_pdf, "rb") as f:
            c1.download_button("Download Reading PDF", f,
                               file_name=f"{scope.subject}_reading_{date_str}.pdf",
                               mime="application/pdf", width="stretch")
    if answers_pdf.exists():
        with open(answers_pdf, "rb") as f:
            c2.download_button("Download Answers PDF", f,
                               file_name=f"{scope.subject}_reading_answers_{date_str}.pdf",
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
