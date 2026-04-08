import streamlit as st

from providers.mlx_provider import MLXProvider, is_available as mlx_available
from storage import mark_flusher
from storage.history_store import migrate_from_old_history
from services.feedback_service import hydrate_all_marks
from ui.components.nav import render as render_nav
from ui.pages import today, progress, history

# One-time migration from old data/history.json → per-day fingerprints.json
migrate_from_old_history()

# Start background flush thread once per process
mark_flusher.start()

# Load all dates into mark buffer at startup (single source of truth)
hydrate_all_marks()


def render():
    st.set_page_config(
        page_title="Jessie Math",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    with st.sidebar:
        st.title("Model")
        mlx_ok = mlx_available()
        options = ["Claude (cloud)"]
        if mlx_ok:
            options.append("Local MLX (Qwen3.5-9B)")

        provider_choice = st.radio("Provider", options)
        if mlx_ok:
            st.caption("Local MLX server detected")
        else:
            st.caption("MLX server offline — using cloud")

    page = render_nav()

    if page == "Today":
        today.render(provider_choice)
    elif page == "History":
        history.render()
    elif page == "Analysis":
        progress.render(provider_choice)
