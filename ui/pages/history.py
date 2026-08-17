import streamlit as st

from domain.daily_task import ALL_TASK_SCOPES, MATH_HOMEWORK, TASK_LABELS
from services import feedback_service
from storage import daily_task_store, homework_store, history_store, reading_store, vocabulary_store, writing_store
from ui.components import marking, question_card


def render():
    st.title("History")

    records = _all_records()
    if not records:
        st.info("No tasks generated yet.")
        return

    labels = [_record_label(record) for record in records]
    selected_label = st.selectbox("Select a task", labels, index=len(labels) - 1)
    record = records[labels.index(selected_label)]

    st.divider()
    _render_header(record)
    st.divider()
    _render_task(record)


def _all_records() -> list[dict]:
    records = daily_task_store.list_task_records(ALL_TASK_SCOPES)
    existing = {(r["scope"], r["date"]) for r in records}
    for date_str in history_store.get_all_dates():
        if (MATH_HOMEWORK, date_str) in existing:
            continue
        task = homework_store.load_questions(date_str)
        if task:
            records.append({
                "scope": MATH_HOMEWORK,
                "date": date_str,
                "subject": "math",
                "task_type": "homework",
                "task": task,
            })
    return sorted(records, key=lambda r: (r["date"], r["subject"], r["task_type"]))


def _record_label(record: dict) -> str:
    return f"{record['date']} · {TASK_LABELS.get(record['scope'], record['scope'].key)}"


def _render_header(record: dict):
    task = record["task"]
    scope = record["scope"]
    label = TASK_LABELS.get(scope, scope.key)

    st.subheader(f"{label} — {record['date']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Subject", record["subject"].title())
    c2.metric("Type", record["task_type"].replace("_", " ").title())
    c3.metric("Est. minutes", task.get("estimated_minutes", "—"))
    feedback_service.hydrate_marks_for(scope, record["date"])
    correct, total = feedback_service.calc_score_for(scope, record["date"])
    c4.metric("Score", f"{correct}/{total}" if total else "—")


def _render_task(record: dict):
    scope = record["scope"]
    task = record["task"]
    date_str = record["date"]
    if scope == MATH_HOMEWORK:
        _render_math(task, date_str)
    elif scope.subject == "english" and scope.task_type == "vocabulary":
        _render_vocabulary(scope, task, date_str)
    elif scope.subject == "english" and scope.task_type == "writing":
        _render_writing(scope, task, date_str)
    else:
        _render_reading(scope, task, date_str)


def _render_math(task: dict, date_str: str):
    tab_q, tab_a = st.tabs(["Questions", "Answers"])
    with tab_q:
        question_card.render_questions_tab(task)
    with tab_a:
        question_card.render_answers_tab(task, date_str, allow_marking=True)
    _render_math_pdf_downloads(date_str)


def _render_vocabulary(scope, task: dict, date_str: str):
    feedback_service.hydrate_marks_for(scope, date_str)
    marking.render_score(scope, date_str, "Mark each vocabulary quick check.")
    for item in task.get("words", []):
        with st.container(border=True):
            st.markdown(f"**{item.get('word', '')}** ({item.get('chinese', '')}) — {item.get('definition', '')}")
            st.markdown(item.get("quick_check", ""))
            st.caption(f"Answer: {item.get('answer', '')}")
            marking.render_mark(scope, date_str, item.get("word", ""))
    _render_vocab_pdf_downloads(date_str)


def _render_reading(scope, task: dict, date_str: str):
    feedback_service.hydrate_marks_for(scope, date_str)
    passage = task.get("passage", {})
    st.markdown(f"### {passage.get('title', 'Passage')}")
    st.write(passage.get("text", ""))
    with st.expander("Questions and answers", expanded=True):
        marking.render_score(scope, date_str, "Mark each reading question.")
        for idx, item in enumerate(task.get("questions", []), 1):
            with st.container(border=True):
                st.markdown(f"**{idx}. {item.get('question', '')}**")
                st.caption(f"Answer: {item.get('answer', '')}")
                marking.render_mark(scope, date_str, item.get("id", f"q_{idx:03d}"))
    _render_reading_pdf_downloads(scope, date_str)


def _render_writing(scope, task: dict, date_str: str):
    feedback_service.hydrate_marks_for(scope, date_str)
    opinion = task.get("opinion", {})
    st.markdown(f"### {opinion.get('memorize_line') or opinion.get('claim', 'Opinion')}")
    if opinion.get("chinese"):
        st.caption(opinion.get("chinese"))
    marking.render_score(scope, date_str, "Mark each memorized writing sentence.")
    _render_writing_mark(scope, date_str, "opinion", "Opinion", opinion.get("memorize_line") or opinion.get("claim", ""))
    for idx, item in enumerate(task.get("examples", []), 1):
        _render_writing_mark(
            scope,
            date_str,
            item.get("id", f"example_{idx:03d}"),
            f"Example {idx}",
            item.get("memorize_line", ""),
        )
    _render_writing_pdf_downloads(date_str)


def _render_writing_mark(scope, date_str: str, item_id: str, label: str, text: str):
    with st.container(border=True):
        st.markdown(f"**{label}**")
        st.markdown(text)
        marking.render_mark(
            scope,
            date_str,
            item_id,
            correct_label="Memorized",
            wrong_label="Needs practice",
        )


def _render_math_pdf_downloads(date_str: str):
    pdf_d = _existing_math_pdf_dir(date_str)
    _download_pair(pdf_d / "questions.pdf", pdf_d / "answers.pdf", "math", date_str)


def _render_vocab_pdf_downloads(date_str: str):
    pdf_d = vocabulary_store.pdf_dir(date_str)
    _download_pair(pdf_d / "vocabulary.pdf", pdf_d / "answers.pdf", "vocabulary", date_str)


def _render_reading_pdf_downloads(scope, date_str: str):
    pdf_d = reading_store.pdf_dir(scope, date_str)
    _download_pair(pdf_d / "reading.pdf", pdf_d / "answers.pdf", f"{scope.subject}_reading", date_str)


def _render_writing_pdf_downloads(date_str: str):
    pdf_d = writing_store.pdf_dir(date_str)
    _download_pair(pdf_d / "writing.pdf", pdf_d / "answers.pdf", "writing", date_str)


def _download_pair(primary, answers, prefix: str, date_str: str):
    c1, c2 = st.columns(2)
    if primary.exists():
        with open(primary, "rb") as f:
            c1.download_button("Download Practice PDF", f,
                               file_name=f"{prefix}_{date_str}.pdf",
                               mime="application/pdf", width="stretch")
    if answers.exists():
        with open(answers, "rb") as f:
            c2.download_button("Download Answers PDF", f,
                               file_name=f"{prefix}_answers_{date_str}.pdf",
                               mime="application/pdf", width="stretch")


def _existing_math_pdf_dir(date_str):
    pdf_d = homework_store.pdf_dir(date_str)
    legacy = homework_store.legacy_pdf_dir(date_str)
    if not (pdf_d / "questions.pdf").exists() and (legacy / "questions.pdf").exists():
        return legacy
    return pdf_d
