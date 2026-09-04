from datetime import date
from html import escape
import re

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
                <h2>Daily Writing Lab</h2>
                <p>Write about 50 words, then revise ideas and one language skill.</p>
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
        st.caption("每天写一个约 50 词的段落；词汇背诵在 Vocabulary 中单独完成。")
        c1, c2 = st.columns([1, 3])
        grade_level = c1.selectbox("Grade", [5, 6, 7, 8], index=1, key="writing_grade")
        focus = c2.text_input(
            "Focus",
            value="academic writing: answer, evidence, explanation, and revision",
            key="writing_focus",
        )

    if not task:
        if st.button("Generate Writing", type="primary", width="stretch", key="writing_generate"):
            _generate(today, provider, grade_level, focus, force=False)
    else:
        st.info("Writing task already generated for today. The reference response stays hidden until Round 1 feedback.")
        if st.button("Regenerate Writing", type="secondary", key="writing_regenerate"):
            _generate(today, provider, grade_level, focus, force=True)

    if task:
        feedback_service.hydrate_marks_for(ENGLISH_WRITING, today)
        _render_task(task, provider)
        st.divider()
        _render_pdf_downloads(task)


def _generate(today: str, provider, grade_level: int, focus: str, force: bool):
    if not _check_api_key(provider):
        return
    if force:
        mark_buffer.clear_for(ENGLISH_WRITING, today)
    with st.spinner("Generating writing lab..."):
        writing_service.generate(today, provider, grade_level=grade_level, focus=focus, force=force)
    st.rerun()


def _render_task(task: dict, provider):
    if task.get("task_version") != 2:
        _render_v1_task(task)
        return

    practice = task.get("practice") or {}
    mode_label = task.get("mode_label") or task.get("writing_mode", "opinion").replace("_", " ").title()
    target_range = task.get("target_range") or [45, 65]
    correct, total = feedback_service.calc_score_for(ENGLISH_WRITING, task["date"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mode", mode_label)
    c2.metric("Target", f"{task.get('target_words', 50)} words")
    c3.metric("Est. minutes", task.get("estimated_minutes", "—"))
    c4.metric("Marked", f"{correct}/{total}" if total else "—")

    with st.expander("Daily plan", expanded=True):
        for item in task.get("time_plan", []):
            st.markdown(f"**{item.get('minutes', '—')} min** — {item.get('activity', '')}")

    source = task.get("source") or {}
    if source.get("text"):
        with st.container(border=True):
            st.markdown('<div class="tm-section-label">Read first</div>', unsafe_allow_html=True)
            st.subheader(source.get("title") or "Source passage")
            st.write(source.get("text"))

    with st.container(border=True):
        st.markdown('<div class="tm-section-label">Your writing prompt</div>', unsafe_allow_html=True)
        st.markdown(f"### {task.get('writing_prompt', 'Write one short paragraph.')}")
        st.caption(
            f"写一个段落，目标 {target_range[0]}–{target_range[1]} 个英文词。"
            "先回答，再给证据，最后解释。"
        )

    st.subheader("Answer / Claim → Evidence → Explain")
    structure = task.get("structure") or []
    cols = st.columns(min(len(structure), 3) or 1)
    for idx, item in enumerate(structure[:3]):
        with cols[idx]:
            st.markdown(f"**{item.get('label', 'Step')}**")
            st.caption(item.get("instruction", ""))
            if item.get("frame"):
                st.code(item["frame"], language=None)

    submission = writing_store.load_submission(task["date"])
    saved_round_1 = submission.get("round_1") or {}
    saved_round_2 = submission.get("round_2") or {}

    st.subheader("Round 1 · Ideas and evidence")
    st.info(practice.get("draft_task", "Write one paragraph of about 50 words."))
    draft = st.text_area(
        "First draft",
        value=saved_round_1.get("draft", ""),
        key=f"writing_draft_{task['date']}",
        height=160,
        placeholder="Write one focused paragraph here...",
    )
    _render_draft_stats(draft, target_range)
    if st.button("Check structure and evidence", type="primary", key=f"writing_review_1_{task['date']}"):
        _request_review(task, draft, 1, provider)
    round_1_feedback = (writing_store.load_submission(task["date"]).get("round_1") or {}).get("feedback")
    if round_1_feedback:
        _render_review(round_1_feedback)
        marking.render_mark(
            ENGLISH_WRITING, task["date"], "draft",
            correct_label="Content revised", wrong_label="Needs another pass",
        )

    st.subheader("Round 2 · One language skill")
    revised = st.text_area(
        "Revised paragraph",
        value=saved_round_2.get("draft", draft),
        key=f"writing_revision_{task['date']}",
        height=160,
        placeholder="Revise the same paragraph after Round 1 feedback...",
    )
    _render_draft_stats(revised, target_range)
    if st.button(
        "Check one language skill",
        key=f"writing_review_2_{task['date']}",
        disabled=not bool(round_1_feedback),
    ):
        _request_review(task, revised, 2, provider)
    round_2_feedback = (writing_store.load_submission(task["date"]).get("round_2") or {}).get("feedback")
    if round_2_feedback:
        _render_review(round_2_feedback)
        marking.render_mark(
            ENGLISH_WRITING, task["date"], "revision",
            correct_label="Revision complete", wrong_label="Needs another pass",
        )

    with st.expander("Self-check", expanded=True):
        for idx, item in enumerate(practice.get("checklist", []), 1):
            st.checkbox(item, key=f"writing_check_{task['date']}_{idx}")

    sample_response = practice.get("sample_response")
    if sample_response and round_1_feedback:
        with st.expander("Reference response · open after revising"):
            st.write(sample_response)


def _request_review(task: dict, draft: str, review_round: int, provider):
    if not _check_api_key(provider):
        return
    with st.spinner("Reviewing the student's paragraph..."):
        try:
            writing_service.review_draft(task, draft, review_round, provider)
        except writing_service.WritingReviewError as exc:
            st.warning(str(exc))
            return
    st.rerun()


def _render_review(feedback: dict):
    with st.container(border=True):
        st.markdown(f"**Strength:** {feedback.get('strength', '')}")
        if feedback.get("answer_feedback"):
            st.markdown(f"**Answer / Claim:** {feedback['answer_feedback']}")
        if feedback.get("evidence_feedback"):
            st.markdown(f"**Evidence / Explain:** {feedback['evidence_feedback']}")
        if feedback.get("language_category"):
            st.markdown(f"**Language focus:** {feedback['language_category']}")
        for item in feedback.get("corrections") or []:
            st.markdown(
                f"`{item.get('original', '')}` → `{item.get('revision', '')}`  "
                f"{item.get('why', '')}"
            )
        st.info(feedback.get("next_step", ""))


def _render_v1_task(task: dict):
    focus_words = task.get("focus_words") or []
    if not focus_words:
        _render_legacy_task(task)
        return

    practice = task.get("practice") or {}
    mode_label = task.get("mode_label") or task.get("writing_mode", "opinion").replace("_", " ").title()
    correct, total = feedback_service.calc_score_for(ENGLISH_WRITING, task["date"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mode", mode_label)
    c2.metric("Focus words", len(focus_words))
    c3.metric("Est. minutes", task.get("estimated_minutes", "—"))
    c4.metric("Marked", f"{correct}/{total}" if total else "—")

    with st.expander("15–20 minute plan", expanded=True):
        for item in task.get("time_plan", []):
            st.markdown(f"**{item.get('minutes', '—')} min** — {item.get('activity', '')}")

    source = task.get("source") or {}
    if source.get("text"):
        with st.container(border=True):
            st.markdown('<div class="tm-section-label">Read first</div>', unsafe_allow_html=True)
            st.subheader(source.get("title") or "Source passage")
            st.write(source.get("text"))

    with st.container(border=True):
        st.markdown('<div class="tm-section-label">Your writing prompt</div>', unsafe_allow_html=True)
        st.markdown(f"### {task.get('writing_prompt', 'Write a three-paragraph short essay.')}")
        st.caption("先回答问题，再给证据，最后解释证据为什么支持你的答案。")

    st.subheader("Answer → Evidence → Explain")
    structure = task.get("structure") or []
    cols = st.columns(min(len(structure), 3) or 1)
    for idx, item in enumerate(structure[:3]):
        with cols[idx]:
            st.markdown(f"**{item.get('label', 'Step')}**")
            st.caption(item.get("instruction", ""))
            if item.get("frame"):
                st.code(item["frame"], language=None)

    paragraph_plan = task.get("paragraph_plan") or []
    if paragraph_plan:
        st.subheader("Three-paragraph short essay")
        for item in paragraph_plan:
            st.markdown(f"**{item.get('label', 'Paragraph')}** — {item.get('purpose', '')}")

    st.subheader("Use the five focus words")
    st.caption("每个词写一个自己的句子；下面的 model 只是参考，不要直接抄写。")
    for idx, item in enumerate(focus_words, 1):
        with st.container(border=True):
            word = item.get("word", "")
            st.markdown(f"**{idx}. {word}** — {item.get('chinese', '')}")
            st.caption(item.get("meaning", ""))
            exercise = next(
                (entry for entry in practice.get("word_sentences", [])
                 if entry.get("word") == word),
                {},
            )
            st.text_area(
                exercise.get("prompt", f"Use {word} in an original sentence."),
                key=f"writing_word_{task['date']}_{word}",
                height=70,
            )
            if exercise.get("model"):
                st.caption(f"Model: {exercise['model']}")
            marking.render_mark(
                ENGLISH_WRITING,
                task["date"],
                f"word_{word}",
                correct_label="Done",
                wrong_label="Needs practice",
            )

    st.subheader("Write and revise")
    st.info(practice.get("draft_task", "Write a three-paragraph, 8-12 sentence first draft."))
    draft = st.text_area(
        "First draft",
        key=f"writing_draft_{task['date']}",
        height=180,
        placeholder="Write your introduction, body, and conclusion here...",
    )
    _render_draft_stats(draft)
    marking.render_mark(
        ENGLISH_WRITING, task["date"], "draft",
        correct_label="Draft complete", wrong_label="Needs practice",
    )

    st.info(practice.get("revision_task", "Revise one sentence and add a specific detail."))
    revised = st.text_area(
        "Revised draft",
        key=f"writing_revision_{task['date']}",
        height=180,
        placeholder="Rewrite your short essay here after checking it...",
    )
    _render_draft_stats(revised)
    marking.render_mark(
        ENGLISH_WRITING, task["date"], "revision",
        correct_label="Revision complete", wrong_label="Needs practice",
    )

    with st.expander("Self-check", expanded=True):
        for idx, item in enumerate(practice.get("checklist", []), 1):
            st.checkbox(item, key=f"writing_check_{task['date']}_{idx}")

    examples = task.get("examples", [])
    if examples:
        with st.expander("Reference sentences — imitate, do not memorize"):
            for idx, item in enumerate(examples, 1):
                sentence = item.get("reference_sentence") or item.get("memorize_line") or item.get("example", "")
                st.markdown(f"**{idx}.** {sentence}")
                if item.get("why_it_works"):
                    st.caption(item["why_it_works"])

    sample_response = practice.get("sample_response")
    if sample_response:
        with st.expander("Reference response — look after writing"):
            st.write(sample_response)


def _render_legacy_task(task: dict):
    """Keep previously generated memory sets readable after the writing upgrade."""
    examples = task.get("examples", [])
    opinion = task.get("opinion", {})
    st.caption("This older task uses the previous memory-set format. New tasks use writing, revision, and vocabulary application.")
    with st.container(border=True):
        st.markdown('<div class="tm-section-label">Opinion reference</div>', unsafe_allow_html=True)
        st.markdown(f"### {opinion.get('memorize_line') or opinion.get('claim', '')}")
        if opinion.get("chinese"):
            st.caption(opinion.get("chinese"))
    with st.expander("Reference sentences"):
        for idx, item in enumerate(examples, 1):
            sentence = item.get("reference_sentence") or item.get("memorize_line") or item.get("example", "")
            st.markdown(f"**{idx}.** {sentence}")
    marking.render_score(ENGLISH_WRITING, task["date"], "Mark the legacy reference sentences.")
    _render_memory_mark("opinion", "Opinion", opinion.get("memorize_line") or opinion.get("claim", ""), task["date"])
    for idx, item in enumerate(examples, 1):
        _render_memory_mark(item.get("id", f"example_{idx:03d}"), f"Example {idx}",
                            item.get("memorize_line") or item.get("example", ""), task["date"])


def _render_draft_stats(text: str, target_range: list[int] | None = None):
    words = len(text.split())
    sentences = len([part for part in re.split(r"[.!?]+", text) if part.strip()])
    status = ""
    if target_range:
        low, high = target_range
        status = " · on target" if low <= words <= high else f" · target {low}–{high}"
    st.caption(f"{words} words · {sentences} sentences{status}")


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
