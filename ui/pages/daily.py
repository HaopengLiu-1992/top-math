from datetime import date

import streamlit as st

from domain.daily_task import ENGLISH_READING, ENGLISH_WRITING, SCIENCE_READING
from pdf.combined_daily_pdf import build_today_answers_pdf, build_today_questions_pdf
from storage import homework_store, reading_store, vocabulary_store, writing_store
from ui.pages import reading, today, vocabulary, writing


def render(provider_choice: str):
    today_str = date.today().isoformat()
    tasks = _daily_task_cards(today_str)

    st.markdown(
        f"""
        <section class="tm-daily-hero">
            <div>
                <div class="tm-kicker">Daily Command Center</div>
                <h1>Jessie's Learning Stack</h1>
                <p>Math, vocabulary, reading, writing, and science in one daily workflow.</p>
            </div>
            <div class="tm-hero-date">
                <span>Today</span>
                <strong>{today_str}</strong>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    _render_daily_overview(tasks)
    _render_combined_pdf_download(today_str)

    selected = st.pills(
        "Daily task",
        [task["key"] for task in tasks],
        default=st.session_state.get("daily_task", "math"),
        format_func=lambda key: next(task["label"] for task in tasks if task["key"] == key),
        label_visibility="collapsed",
        key="daily_task_selector",
        width="stretch",
    )
    if selected:
        st.session_state["daily_task"] = selected

    st.markdown('<div class="tm-workspace-shell">', unsafe_allow_html=True)
    if st.session_state.get("daily_task", "math") == "math":
        today.render(provider_choice, embedded=True)
    elif st.session_state["daily_task"] == "vocabulary":
        vocabulary.render(provider_choice, embedded=True)
    elif st.session_state["daily_task"] == "english_reading":
        reading.render(ENGLISH_READING, provider_choice)
    elif st.session_state["daily_task"] == "english_writing":
        writing.render(provider_choice)
    else:
        reading.render(SCIENCE_READING, provider_choice)
    st.markdown("</div>", unsafe_allow_html=True)


def _daily_task_cards(date_str: str) -> list[dict]:
    math_task = homework_store.load_questions(date_str)
    vocab_task = vocabulary_store.load_task(date_str)
    english_task = reading_store.load_task(ENGLISH_READING, date_str)
    writing_task = writing_store.load_task(date_str)
    science_task = reading_store.load_task(SCIENCE_READING, date_str)

    return [
        {
            "key": "math",
            "label": "Math",
            "eyebrow": "Core practice",
            "status": "Ready" if math_task else "Not generated",
            "detail": _math_detail(math_task),
            "accent": "red",
        },
        {
            "key": "vocabulary",
            "label": "Vocabulary",
            "eyebrow": "20 academic words",
            "status": "Ready" if vocab_task else "Not generated",
            "detail": _vocab_detail(vocab_task),
            "accent": "blue",
        },
        {
            "key": "english_reading",
            "label": "English Reading",
            "eyebrow": "Comprehension",
            "status": "Ready" if english_task else "Not generated",
            "detail": _reading_detail(english_task),
            "accent": "green",
        },
        {
            "key": "english_writing",
            "label": "English Writing",
            "eyebrow": "Opinion + examples",
            "status": "Ready" if writing_task else "Not generated",
            "detail": _writing_detail(writing_task),
            "accent": "violet",
        },
        {
            "key": "science_reading",
            "label": "Science Reading",
            "eyebrow": "Evidence reading",
            "status": "Ready" if science_task else "Not generated",
            "detail": _reading_detail(science_task),
            "accent": "amber",
        },
    ]


def _render_daily_overview(tasks: list[dict]):
    cols = st.columns(len(tasks))
    for col, task in zip(cols, tasks):
        state_class = "is-ready" if task["status"] == "Ready" else "is-pending"
        col.markdown(
            f"""
            <article class="tm-task-card tm-accent-{task['accent']} {state_class}">
                <div class="tm-task-topline">
                    <span>{task['eyebrow']}</span>
                    <strong>{task['status']}</strong>
                </div>
                <h3>{task['label']}</h3>
                <p>{task['detail']}</p>
            </article>
            """,
            unsafe_allow_html=True,
        )


def _render_combined_pdf_download(date_str: str):
    questions_pdf, question_included, question_missing = build_today_questions_pdf(date_str)
    answers_pdf, answer_included, answer_missing = build_today_answers_pdf(date_str)
    with st.container(border=True):
        st.markdown('<div class="tm-section-label">One-click download</div>', unsafe_allow_html=True)
        if not questions_pdf and not answers_pdf:
            st.info("No PDFs found for today yet.")
            return

        c1, c2 = st.columns(2)
        if questions_pdf:
            with open(questions_pdf, "rb") as f:
                c1.download_button(
                    "Download Questions",
                    f,
                    file_name=f"topmath_{date_str}_questions.pdf",
                    mime="application/pdf",
                    width="stretch",
                    key="download_today_questions_pdf",
                )
        else:
            c1.info("No question PDFs found.")

        if answers_pdf:
            with open(answers_pdf, "rb") as f:
                c2.download_button(
                    "Download Answers",
                    f,
                    file_name=f"topmath_{date_str}_answers.pdf",
                    mime="application/pdf",
                    width="stretch",
                    key="download_today_answers_pdf",
                )
        else:
            c2.info("No answer PDFs found.")

        st.caption(
            f"Questions: {len(question_included)} PDF(s). "
            f"Answers: {len(answer_included)} PDF(s)."
        )
        missing = question_missing + answer_missing
        if missing:
            with st.expander("Missing PDFs"):
                for part in missing:
                    st.markdown(f"- {part.label}")


def _math_detail(task: dict | None) -> str:
    if not task:
        return "Grade 5-8 topic-based generation."
    topic = task.get("target_topic", {}).get("title") or task.get("target_topic", {}).get("id")
    return topic or f"Grade {task.get('grade_level', '-')}, day {task.get('day', '-')}"


def _vocab_detail(task: dict | None) -> str:
    if not task:
        return "Local index selects words; LLM writes practice."
    words = task.get("words", [])
    new_count = sum(1 for word in words if not word.get("is_review"))
    review_count = len(words) - new_count
    return f"{new_count} new · {review_count} review words"


def _reading_detail(task: dict | None) -> str:
    if not task:
        return "Passage, vocabulary, questions, answers."
    passage = task.get("passage", {})
    return passage.get("title") or f"{len(task.get('questions', []))} questions"


def _writing_detail(task: dict | None) -> str:
    if not task:
        return "One opinion and three examples to memorize."
    opinion = task.get("opinion", {})
    return opinion.get("claim") or opinion.get("memorize_line") or "Memory set ready"
