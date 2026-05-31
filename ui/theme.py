import streamlit as st


def apply_theme():
    st.markdown("""
    <style>
    :root {
        --tm-bg: #f6f7f9;
        --tm-panel: #ffffff;
        --tm-panel-soft: #fbfcfd;
        --tm-border: #dfe3e8;
        --tm-border-strong: #cbd5df;
        --tm-text: #202532;
        --tm-muted: #6b7280;
        --tm-accent: #e94b5a;
        --tm-accent-dark: #c92f42;
        --tm-teal: #0f766e;
        --tm-blue: #2563eb;
        --tm-green: #188f5f;
        --tm-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    .stApp {
        background: var(--tm-bg);
        color: var(--tm-text);
    }

    .block-container {
        max-width: 1460px;
        padding-top: 4rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: var(--tm-text);
        letter-spacing: 0;
    }

    h1 {
        font-size: 2.15rem !important;
        font-weight: 760 !important;
        margin-bottom: 1.1rem !important;
    }

    h2, h3 {
        font-weight: 700 !important;
    }

    div[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--tm-border);
    }

    div[data-testid="stMetric"] {
        background: var(--tm-panel);
        border: 1px solid var(--tm-border);
        border-radius: 8px;
        padding: 0.9rem 1rem;
        box-shadow: var(--tm-shadow);
    }

    div[data-testid="stMetricLabel"] p {
        color: var(--tm-muted) !important;
        font-size: 0.78rem !important;
        font-weight: 650 !important;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }

    div[data-testid="stMetricValue"] {
        color: var(--tm-text) !important;
        font-size: 1.55rem !important;
        letter-spacing: 0 !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--tm-border) !important;
        border-radius: 8px !important;
        background: var(--tm-panel) !important;
        box-shadow: var(--tm-shadow);
    }

    div[data-testid="stForm"],
    div[data-testid="stExpander"] {
        border-color: var(--tm-border) !important;
        border-radius: 8px !important;
        background: var(--tm-panel) !important;
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-testid="stDateInput"] input {
        border-radius: 8px !important;
        border-color: var(--tm-border) !important;
        background: var(--tm-panel-soft) !important;
    }

    button[kind="primary"],
    div[data-testid="stDownloadButton"] button[kind="primary"] {
        background: var(--tm-accent) !important;
        border-color: var(--tm-accent) !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }

    button[kind="primary"]:hover {
        background: var(--tm-accent-dark) !important;
        border-color: var(--tm-accent-dark) !important;
    }

    button[kind="secondary"] {
        background: #ffffff !important;
        border-color: var(--tm-border-strong) !important;
        color: var(--tm-text) !important;
        border-radius: 8px !important;
        font-weight: 650 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
        border-bottom: 1px solid var(--tm-border);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.75rem 1rem;
        font-weight: 650;
    }

    .stTabs [aria-selected="true"] {
        color: var(--tm-accent) !important;
    }

    div[data-testid="stAlert"] {
        border-radius: 8px;
        border: 1px solid var(--tm-border);
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--tm-border);
        border-radius: 8px;
        overflow: hidden;
    }

    code, pre {
        border-radius: 8px !important;
    }

    hr {
        border-color: var(--tm-border) !important;
        margin: 1.4rem 0 !important;
    }

    .tm-nav-shell {
        background: #ffffff;
        border: 1px solid var(--tm-border);
        border-radius: 8px;
        padding: 0.35rem;
        box-shadow: var(--tm-shadow);
        margin-top: 1.4rem;
        margin-bottom: 1.6rem;
    }

    div[data-testid="stSegmentedControl"],
    div[data-testid="stPills"],
    div[data-testid="stButtonGroup"] {
        background: #ffffff;
        border: 1px solid var(--tm-border);
        border-radius: 8px;
        box-sizing: border-box;
        width: 100%;
        max-width: 100%;
        padding: 0.35rem;
        box-shadow: var(--tm-shadow);
        margin-top: 1.4rem;
        margin-bottom: 1.6rem;
        overflow: hidden;
    }

    div[data-testid="stButtonGroup"] > label {
        display: none;
    }

    div[data-testid="stButtonGroup"] div[role="radiogroup"] {
        display: grid !important;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.3rem;
        width: 100%;
    }

    div[data-testid="stButtonGroup"] button {
        width: 100%;
        justify-content: center;
        border-radius: 8px !important;
        min-width: 0;
    }

    div[data-testid="stSegmentedControl"] div[role="radiogroup"],
    div[data-testid="stPills"] div[role="radiogroup"] {
        display: flex;
        gap: 0.3rem;
        width: 100%;
    }

    div[data-testid="stSegmentedControl"] label,
    div[data-testid="stPills"] label {
        flex: 1 1 0;
        justify-content: center;
        min-width: 0;
        border-radius: 8px !important;
    }

    div[data-testid="stSegmentedControl"] label p,
    div[data-testid="stPills"] label p {
        font-weight: 700;
        white-space: nowrap;
    }

    .tm-section-label {
        color: var(--tm-muted);
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.45rem;
    }

    .tm-panel-title {
        font-size: 1.05rem;
        font-weight: 740;
        margin-bottom: 0.75rem;
        color: var(--tm-text);
    }

    .tm-muted {
        color: var(--tm-muted);
    }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        div[data-testid="stSegmentedControl"] div[role="radiogroup"],
        div[data-testid="stPills"] div[role="radiogroup"] {
            flex-direction: column;
        }

        div[data-testid="stButtonGroup"] div[role="radiogroup"] {
            grid-template-columns: 1fr;
        }

        div[data-testid="stSegmentedControl"] label,
        div[data-testid="stPills"] label {
            width: 100%;
        }
    }
    </style>
    """, unsafe_allow_html=True)
