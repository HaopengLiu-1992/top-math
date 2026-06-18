from datetime import date

import streamlit as st

from providers.provider_resolver import resolve_provider
from services import vocabulary_service
from settings import secrets
from providers.anthropic_provider import AnthropicProvider
from providers.deepseek_provider import DeepSeekProvider
from providers.gemini_provider import GeminiProvider
from storage import vocabulary_store


def render(provider_choice: str):
    today = date.today().isoformat()
    st.title(f"🔤 Vocabulary — {today}")

    provider = resolve_provider(provider_choice)
    task = vocabulary_store.load_task(today)

    with st.container(border=True):
        st.markdown('<div class="tm-section-label">Vocabulary setup</div>', unsafe_allow_html=True)
        grade_level = st.selectbox("Grade", [5, 6, 7, 8], index=1)

    if not task:
        if st.button("Generate Vocabulary", type="primary", width="stretch"):
            _generate(today, provider, grade_level, force=False)
    else:
        st.info("Vocabulary already generated for today.")
        if st.button("Regenerate Vocabulary", type="secondary"):
            _generate(today, provider, grade_level, force=True)

    if task:
        _render_task(task)
        st.divider()
        _render_pdf_downloads(today)


def _generate(today: str, provider, grade_level: int, force: bool):
    if not _check_api_key(provider):
        return
    with st.spinner("Generating vocabulary..."):
        vocabulary_service.generate(today, provider, grade_level=grade_level, force=force)
    st.rerun()


def _render_task(task: dict):
    words = task.get("words", [])
    new_count = sum(1 for w in words if not w.get("is_review"))
    review_count = sum(1 for w in words if w.get("is_review"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Words", len(words))
    c2.metric("New", new_count)
    c3.metric("Review", review_count)
    c4.metric("Model", task.get("model", "—"))

    st.subheader("Words")
    for item in words:
        label = "Review" if item.get("is_review") else "New"
        with st.container(border=True):
            st.markdown(f"**{item.get('word', '')}** · {label} · {item.get('category', '')}")
            st.markdown(f"{item.get('chinese', '')} — {item.get('definition', '')}")
            st.caption(item.get("example", ""))
            st.markdown(f"Quick check: {item.get('quick_check', '')}")

    practice = task.get("practice", {})
    tab_m, tab_f, tab_k = st.tabs(["Matching", "Fill Blank", "Reading Bridge"])
    with tab_m:
        for item in practice.get("matching", []):
            st.markdown(f"- **{item.get('word', '')}** → {item.get('definition', '')}")
    with tab_f:
        for item in practice.get("fill_blank", []):
            st.markdown(f"- {item.get('sentence', '')}")
            st.caption(f"Answer: {item.get('answer', '')}")
    with tab_k:
        for item in practice.get("keyword_reading", []):
            st.markdown(f"- {item.get('question', '')}")
            st.caption(f"Keyword: {item.get('keyword', '')} — {item.get('meaning', '')}")


def _render_pdf_downloads(date_str: str):
    pdf_d = vocabulary_store.pdf_dir(date_str)
    vocab_pdf = pdf_d / "vocabulary.pdf"
    answers_pdf = pdf_d / "answers.pdf"
    c1, c2 = st.columns(2)
    if vocab_pdf.exists():
        with open(vocab_pdf, "rb") as f:
            c1.download_button("Download Vocabulary PDF", f,
                               file_name=f"vocabulary_{date_str}.pdf",
                               mime="application/pdf", width="stretch")
    if answers_pdf.exists():
        with open(answers_pdf, "rb") as f:
            c2.download_button("Download Answers PDF", f,
                               file_name=f"vocabulary_answers_{date_str}.pdf",
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
