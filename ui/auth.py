import hmac

import streamlit as st

from settings import secrets


def require_app_password():
    if not secrets.auth_required():
        return

    password = secrets.app_password()
    if not password:
        st.error("APP_PASSWORD is not configured.")
        st.caption("Set AUTH_REQUIRED=true and APP_PASSWORD in Streamlit Secrets.")
        st.stop()

    if st.session_state.get("authenticated"):
        return

    st.title("Jessie Math")
    st.caption("Enter the app password to continue.")
    with st.form("app_password_form"):
        entered = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Unlock", type="primary")

    if submitted:
        if hmac.compare_digest(entered, password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()
