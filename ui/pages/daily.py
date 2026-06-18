from datetime import date

import streamlit as st

from domain.daily_task import ENGLISH_READING, SCIENCE_READING
from storage import homework_store, reading_store, vocabulary_store
from ui.pages import reading, today, vocabulary


def render(provider_choice: str):
    today_str = date.today().isoformat()
    tasks = _daily_task_cards(today_str)

    st.markdown(
        f"""
        <section class="tm-daily-hero">
            <div>
                <div class="tm-kicker">Daily Command Center</div>
                <h1>Jessie's Learning Stack</h1>
                <p>Math, academic vocabulary, English reading, and science reading in one daily workflow.</p>
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
    else:
        reading.render(SCIENCE_READING, provider_choice)
    st.markdown("</div>", unsafe_allow_html=True)


def _daily_task_cards(date_str: str) -> list[dict]:
    math_task = homework_store.load_questions(date_str)
    vocab_task = vocabulary_store.load_task(date_str)
    english_task = reading_store.load_task(ENGLISH_READING, date_str)
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
            "key": "science_reading",
            "label": "Science Reading",
            "eyebrow": "Evidence reading",
            "status": "Ready" if science_task else "Not generated",
            "detail": _reading_detail(science_task),
            "accent": "amber",
        },
    ]


def _render_daily_overview(tasks: list[dict]):
    cols = st.columns(4)
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
