import streamlit as st


def apply_theme():
    st.markdown("""
    <style>
    :root {
        --tm-bg: #f3f5f8;
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
        --tm-amber: #b7791f;
        --tm-ink: #111827;
        --tm-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        --tm-shadow-lift: 0 18px 45px rgba(18, 25, 38, 0.08);
    }

    .stApp {
        background:
            radial-gradient(circle at 14% 8%, rgba(37, 99, 235, 0.10), transparent 24rem),
            linear-gradient(180deg, #f8fafc 0%, var(--tm-bg) 38%, #eef2f6 100%);
        color: var(--tm-text);
    }

    .block-container {
        max-width: 1460px;
        padding-top: 3.2rem;
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
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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

    .tm-daily-hero {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 2rem;
        min-height: 14rem;
        padding: 2rem;
        margin-bottom: 1.2rem;
        border: 1px solid rgba(124, 139, 161, 0.28);
        border-radius: 18px;
        color: #ffffff;
        background:
            linear-gradient(135deg, rgba(13, 18, 30, 0.94), rgba(31, 41, 55, 0.90)),
            linear-gradient(90deg, rgba(233, 75, 90, 0.52), rgba(37, 99, 235, 0.44), rgba(15, 118, 110, 0.38));
        box-shadow: var(--tm-shadow-lift);
        overflow: hidden;
        position: relative;
    }

    .tm-daily-hero::after {
        content: "";
        position: absolute;
        inset: auto -8rem -10rem auto;
        width: 24rem;
        height: 24rem;
        border: 1px solid rgba(255, 255, 255, 0.13);
        border-radius: 999px;
    }

    .tm-daily-hero h1 {
        color: #ffffff !important;
        font-size: 3.45rem !important;
        line-height: 0.98 !important;
        margin: 0.4rem 0 0.8rem !important;
        max-width: 760px;
    }

    .tm-daily-hero p {
        color: rgba(255, 255, 255, 0.78);
        font-size: 1.05rem;
        max-width: 720px;
        margin: 0;
    }

    .tm-kicker {
        color: rgba(255, 255, 255, 0.72);
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }

    .tm-hero-date {
        min-width: 190px;
        padding: 1rem 1.1rem;
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        text-align: right;
        position: relative;
        z-index: 1;
    }

    .tm-hero-date span {
        display: block;
        color: rgba(255, 255, 255, 0.62);
        font-size: 0.76rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .tm-hero-date strong {
        display: block;
        color: #ffffff;
        font-size: 1.25rem;
        margin-top: 0.25rem;
    }

    .tm-task-card {
        min-height: 9.25rem;
        padding: 1.05rem;
        border: 1px solid rgba(148, 163, 184, 0.32);
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.82);
        box-shadow: 0 8px 28px rgba(18, 25, 38, 0.055);
        position: relative;
        overflow: hidden;
    }

    .tm-task-card::before {
        content: "";
        position: absolute;
        left: 0;
        right: 0;
        top: 0;
        height: 4px;
        background: var(--tm-card-accent);
    }

    .tm-task-card h3 {
        margin: 1.05rem 0 0.45rem !important;
        color: var(--tm-ink);
        font-size: 1.08rem !important;
    }

    .tm-task-card p {
        color: var(--tm-muted);
        margin: 0;
        font-size: 0.92rem;
        line-height: 1.4;
    }

    .tm-task-topline {
        display: flex;
        justify-content: space-between;
        gap: 0.8rem;
        align-items: center;
    }

    .tm-task-topline span {
        color: var(--tm-muted);
        font-size: 0.72rem;
        font-weight: 780;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    .tm-task-topline strong {
        color: var(--tm-status-color);
        font-size: 0.78rem;
        font-weight: 800;
    }

    .tm-accent-red { --tm-card-accent: linear-gradient(90deg, #e94b5a, #f59e0b); }
    .tm-accent-blue { --tm-card-accent: linear-gradient(90deg, #2563eb, #06b6d4); }
    .tm-accent-green { --tm-card-accent: linear-gradient(90deg, #188f5f, #84cc16); }
    .tm-accent-amber { --tm-card-accent: linear-gradient(90deg, #b7791f, #ef4444); }
    .tm-accent-violet { --tm-card-accent: linear-gradient(90deg, #7c3aed, #2563eb); }
    .tm-task-card.is-ready { --tm-status-color: var(--tm-green); }
    .tm-task-card.is-pending { --tm-status-color: var(--tm-amber); }

    .tm-workspace-shell {
        margin-top: 1.2rem;
        padding: 1.2rem 0 0;
        border-top: 1px solid rgba(148, 163, 184, 0.28);
    }

    .tm-module-heading {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem;
        margin: 1.2rem 0 1rem;
    }

    .tm-module-heading h2 {
        margin: 0 !important;
        font-size: 1.65rem !important;
    }

    .tm-module-heading p {
        margin: 0.2rem 0 0;
        color: var(--tm-muted);
    }

    .tm-chip {
        display: inline-flex;
        align-items: center;
        min-height: 2rem;
        padding: 0.25rem 0.7rem;
        border: 1px solid var(--tm-border);
        border-radius: 999px;
        background: #ffffff;
        color: var(--tm-muted);
        font-weight: 700;
        font-size: 0.78rem;
        white-space: nowrap;
    }

    .tm-word-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
        gap: 0.8rem;
        margin: 0.8rem 0 1rem;
    }

    .tm-word-card {
        border: 1px solid rgba(148, 163, 184, 0.36);
        border-radius: 12px;
        padding: 0.9rem;
        background: #ffffff;
        min-height: 10.5rem;
    }

    .tm-word-card strong {
        display: block;
        color: var(--tm-ink);
        font-size: 1.08rem;
        margin-bottom: 0.25rem;
    }

    .tm-word-card em {
        color: var(--tm-accent);
        font-style: normal;
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .tm-word-card p {
        color: var(--tm-text);
        margin: 0.45rem 0;
        line-height: 1.38;
    }

    .tm-word-card small {
        color: var(--tm-muted);
        line-height: 1.35;
    }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .tm-daily-hero {
            align-items: stretch;
            flex-direction: column;
            padding: 1.25rem;
            min-height: auto;
        }

        .tm-daily-hero h1 {
            font-size: 2.15rem !important;
        }

        .tm-hero-date {
            text-align: left;
            min-width: 0;
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
