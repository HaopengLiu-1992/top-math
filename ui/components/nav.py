import streamlit as st

PAGES = [
    ("📚  Today", "Today"),
    ("📅  History", "History"),
    ("📊  Analysis", "Analysis"),
]


def render() -> str:
    if "page" not in st.session_state:
        st.session_state.page = "Today"

    labels = {key: label for label, key in PAGES}
    selected = st.pills(
        "Navigation",
        [key for _, key in PAGES],
        default=st.session_state.page,
        format_func=lambda value: labels[value],
        label_visibility="collapsed",
        width="stretch",
    )
    if selected:
        st.session_state.page = selected

    st.divider()
    return st.session_state.page
