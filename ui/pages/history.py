import streamlit as st

from storage import homework_store, history_store
from services import feedback_service
from ui.components import question_card


def render():
    st.title("📅 History")

    dates = history_store.get_all_dates()
    if not dates:
        st.info("No homework generated yet.")
        return

    selected = st.selectbox("Select a date", sorted(dates, reverse=True))
    if not selected:
        return

    homework = homework_store.load_questions(selected)
    if not homework:
        st.warning(f"Raw data not found for {selected}.")
        return

    st.divider()
    _render_day_header(homework, selected)
    st.divider()

    tab_q, tab_a = st.tabs(["Questions", "Answers"])

    with tab_q:
        question_card.render_questions_tab(homework)

    with tab_a:
        question_card.render_answers_tab(homework, selected, allow_marking=True)

    st.divider()
    _render_pdf_downloads(selected)


def _render_day_header(homework: dict, date_str: str):
    session_type = homework.get("session_type", "normal")
    correct, total = feedback_service.calc_auto_score(date_str)

    label = "Sunday Review" if session_type == "review" else f"Day {homework.get('day', '-')}"
    st.subheader(f"{label} — {date_str}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Session", session_type.capitalize())
    c2.metric("Est. minutes", homework.get("estimated_minutes", "—"))
    c3.metric("Score", f"{correct}/{total}" if total else "—")


def _render_pdf_downloads(date_str: str):
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
