import os

try:
    import streamlit as st
except ImportError:
    st = None


def get_secret(name: str, default: str | None = None) -> str | None:
    value = _get_streamlit_secret(name)
    if value is not None:
        return value
    return os.environ.get(name, default)


def require_secret(name: str) -> str:
    value = get_secret(name)
    if not value:
        raise RuntimeError(f"{name} is not configured.")
    return value


def is_enabled(name: str, default: bool = False) -> bool:
    value = get_secret(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def auth_required() -> bool:
    return is_enabled("AUTH_REQUIRED", default=False)


def app_password() -> str | None:
    return get_secret("APP_PASSWORD")


def gemini_api_key() -> str | None:
    return get_secret("GEMINI_API_KEY")


def anthropic_api_key() -> str | None:
    return get_secret("ANTHROPIC_API_KEY")


def deepseek_api_key() -> str | None:
    return get_secret("DEEPSEEK_API_KEY")


def _get_streamlit_secret(name: str) -> str | None:
    if st is None:
        return None
    try:
        value = st.secrets.get(name)
    except Exception:
        return None
    if value in ("", None):
        return None
    return str(value)
