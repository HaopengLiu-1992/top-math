import streamlit as st

from domain.daily_task import ENGLISH_READING, SCIENCE_READING
from ui.pages import reading, today, vocabulary


def render(provider_choice: str):
    st.title("Daily Learning")
    st.caption("Math, vocabulary, English reading, and science reading for today's practice.")
    tabs = st.tabs(["Math", "Vocabulary", "English Reading", "Science Reading"])

    with tabs[0]:
        today.render(provider_choice, embedded=True)
    with tabs[1]:
        vocabulary.render(provider_choice, embedded=True)
    with tabs[2]:
        reading.render(ENGLISH_READING, provider_choice)
    with tabs[3]:
        reading.render(SCIENCE_READING, provider_choice)
