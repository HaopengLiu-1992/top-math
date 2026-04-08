import streamlit as st

PAGES = [
    ("📚  Today", "Today"),
    ("📅  History", "History"),
    ("📊  Analysis", "Analysis"),
]


def render() -> str:
    if "page" not in st.session_state:
        st.session_state.page = "Today"

    st.markdown("""
    <style>
    div[data-testid="column"] button {
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.95rem;
    }
    </style>
    """, unsafe_allow_html=True)

    cols = st.columns(len(PAGES))
    for col, (label, key) in zip(cols, PAGES):
        active = st.session_state.page == key
        if col.button(label, width="stretch",
                      type="primary" if active else "secondary"):
            st.session_state.page = key
            st.rerun()

    st.divider()
    return st.session_state.page
