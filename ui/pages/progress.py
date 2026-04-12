from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from services import analysis_service, feedback_report_service, feedback_service
from services.review_service import is_sunday
from storage import history_store, homework_store

TOPIC_NAMES = {
    "5.NBT.A.1": "Place Value",
    "5.NBT.A.2": "Powers of 10",
    "5.NBT.A.3": "Read & Write Decimals",
    "5.NBT.A.4": "Rounding Decimals",
    "5.NBT.B.5": "Multi-digit Multiplication",
    "5.NBT.B.6": "Division with Remainders",
    "5.NBT.B.7": "Decimal Operations",
    "5.NF.A.1": "Adding & Subtracting Fractions",
    "5.NF.A.2": "Fraction Word Problems",
    "5.NF.B.3": "Fractions as Division",
    "5.NF.B.4": "Multiplying Fractions",
    "5.NF.B.5": "Scaling with Fractions",
    "5.NF.B.6": "Fraction Multiplication Problems",
    "5.NF.B.7": "Dividing with Fractions",
    "5.OA.A.1": "Order of Operations",
    "5.OA.A.2": "Write Expressions",
    "5.OA.B.3": "Patterns & Graphs",
    "5.MD.A.1": "Unit Conversions",
    "5.MD.B.2": "Line Plots with Fractions",
    "5.MD.C.3": "Understanding Volume",
    "5.MD.C.4": "Counting Volume",
    "5.MD.C.5": "Volume Formulas",
    "5.G.A.1": "Coordinate Plane",
    "5.G.A.2": "Graphing Points",
    "5.G.B.3": "Properties of Shapes",
    "5.G.B.4": "Classifying Shapes",
}


def _build_df() -> pd.DataFrame:
    """Build dataframe from per-day homework.json + live scores from mark_buffer."""
    rows = []
    for d in history_store.get_all_dates():
        hw = homework_store.load_questions(d)
        if not hw:
            continue
        meta = homework_store.load_meta(d)
        topics = list({data["topic"] for data in meta.values() if data.get("topic")})
        correct, total = feedback_service.calc_auto_score(d)
        score_pct = round(correct / total * 100, 1) if total > 0 and correct > 0 else None
        rows.append({
            "date": d,
            "day": hw.get("day"),
            "session_type": hw.get("session_type", "normal"),
            "topics": topics,
            "score_pct": score_pct,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
    return df


def _get_available_sundays() -> list[str]:
    """Return all Sundays that have a stored analysis or feedback report, newest first."""
    from services import analysis_service
    sundays = []
    for d in history_store.get_all_dates():
        if date.fromisoformat(d).weekday() == 6:  # Sunday
            if (analysis_service.load_analysis(d) or
                    feedback_report_service.load_report(d)):
                sundays.append(d)
    return sorted(sundays, reverse=True)


def render(provider_choice: str):
    st.title("📊 Analysis")

    dates = history_store.get_all_dates()
    if not dates:
        st.info("No homework generated yet. Go to Today to get started.")
        return

    df = _build_df()
    today = date.today().isoformat()

    # ── week selector ─────────────────────────────────────────────────────────
    past_sundays = _get_available_sundays()
    is_current_sunday = is_sunday()

    if past_sundays:
        options = past_sundays.copy()
        if is_current_sunday and today not in options:
            options = [today] + options
        label_map = {d: f"{d} {'(today)' if d == today else ''}" for d in options}
        selected_week = st.selectbox(
            "Week", options, format_func=lambda d: label_map[d]
        )
    else:
        selected_week = today

    st.divider()

    _render_metrics(df)
    st.divider()
    _render_streak(df)
    st.divider()
    _render_daily_scores(df)
    _render_topic_coverage(df)
    _render_weekly_feedback_report(provider_choice, selected_week)
    _render_weekly_analysis(provider_choice, selected_week)

    st.subheader("All Days")
    display_df = df[["date", "day", "session_type", "score_pct", "topics"]].sort_values(
        "date", ascending=False
    ).copy()
    display_df["score_pct"] = display_df["score_pct"].apply(
        lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
    )
    st.dataframe(display_df, width="stretch")


def _render_metrics(df: pd.DataFrame):
    scored = df[df["score_pct"].notna()]
    reviews = int((df["session_type"] == "review").sum()) if "session_type" in df.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Days", len(df))
    c2.metric("Reviews Done", reviews)

    if not scored.empty:
        avg = scored["score_pct"].mean()
        recent = scored["score_pct"].tail(5).mean()
        c3.metric("Avg Score", f"{avg:.1f}%")
        c4.metric("Last 5 Avg", f"{recent:.1f}%")
    else:
        c3.metric("Avg Score", "—")
        c4.metric("Last 5 Avg", "—")


def _render_streak(df: pd.DataFrame):
    today = date.today()
    logged = set(df["date"].dt.date.astype(str))
    streak = 0
    check = today
    while check.isoformat() in logged:
        streak += 1
        check -= timedelta(days=1)
    st.markdown(f"**Current streak: {streak} day{'s' if streak != 1 else ''}** 🔥")


def _render_daily_scores(df: pd.DataFrame):
    scored = df[df["score_pct"].notna()].copy()
    if scored.empty:
        return

    st.subheader("Daily Scores")
    scored["label"] = scored["date"].dt.strftime("%m/%d")
    fig = px.bar(
        scored, x="label", y="score_pct",
        labels={"label": "Date", "score_pct": "Score %"},
        color="score_pct",
        color_continuous_scale=["#c0392b", "#f39c12", "#27ae60"],
        range_color=[0, 100],
    )
    fig.add_hline(y=90, line_dash="dash", line_color="green",
                  annotation_text="90% target", annotation_position="top right")
    fig.update_layout(yaxis_range=[0, 105], height=300,
                      margin=dict(l=0, r=0, t=20, b=0),
                      coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")


def _render_topic_coverage(df: pd.DataFrame):
    all_topics = []
    for topics in df["topics"].dropna():
        if isinstance(topics, list):
            all_topics.extend(topics)
    if not all_topics:
        return

    st.subheader("Topics Practiced")
    readable = [TOPIC_NAMES.get(t, t) for t in all_topics]
    counts = pd.Series(readable).value_counts().reset_index()
    counts.columns = ["topic", "count"]
    fig = px.bar(counts, x="topic", y="count", color="count",
                 color_continuous_scale="Blues",
                 labels={"topic": "Topic", "count": "Days practiced"})
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0),
                      coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")


def _render_weekly_feedback_report(provider_choice: str, selected_week: str):
    st.subheader("Weekly Feedback Report")
    today = date.today().isoformat()
    report = feedback_report_service.load_report(selected_week)

    if report:
        _display_feedback_report(report)
    elif selected_week == today and is_sunday():
        if st.button("Generate Weekly Feedback Report", type="primary"):
            from providers.anthropic_provider import AnthropicProvider
            from providers.gemini_provider import GeminiProvider
            from providers.mlx_provider import MLXProvider
            if provider_choice.startswith("Local"):
                provider = MLXProvider()
            elif provider_choice.startswith("Gemini"):
                provider = GeminiProvider()
            else:
                provider = AnthropicProvider()
            with st.spinner("Generating feedback report..."):
                try:
                    report = feedback_report_service.generate_report(today, provider)
                    _display_feedback_report(report)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")
    else:
        st.caption("No feedback report for this week." if selected_week != today
                   else "Weekly feedback report is generated on Sundays.")


def _display_feedback_report(report: dict):
    st.markdown(f"### {report.get('headline', '')}")

    summary = report.get("score_summary", {})
    c1, c2, c3 = st.columns(3)
    c1.metric("Days completed", summary.get("days_completed", "—"))
    avg = summary.get("avg_score_pct")
    c2.metric("Avg score", f"{avg:.1f}%" if avg else "—")
    trend = summary.get("trend", "")
    trend_emoji = {"improving": "📈", "declining": "📉", "stable": "➡️"}.get(trend, "")
    c3.metric("Trend", f"{trend_emoji} {trend}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Strengths**")
        for s in report.get("strengths", []):
            st.markdown(f"- {s}")
    with col2:
        st.markdown("**Areas to improve**")
        for w in report.get("weaknesses", []):
            with st.expander(f"{w.get('topic', '')} — {w.get('description', '')[:60]}..."):
                st.markdown(f"**Example:** {w.get('example_question', '')}")
                st.markdown(f"**Tip:** {w.get('tip', '')}")

    plan = report.get("next_week_plan", {})
    if plan:
        st.markdown("**Next week plan**")
        st.markdown(f"- Primary focus: {plan.get('primary_focus', '')}")
        st.markdown(f"- Secondary focus: {plan.get('secondary_focus', '')}")
        st.markdown(f"- Extra practice: {plan.get('suggested_extra_practice', '')}")

    st.info(report.get("encouragement", ""))
    st.divider()


def _render_weekly_analysis(provider_choice: str, selected_week: str):
    st.subheader("Weekly Analysis")
    today = date.today().isoformat()
    existing = analysis_service.load_analysis(selected_week)

    if existing:
        _display_analysis(existing)
    elif selected_week == today and is_sunday():
        if st.button("Generate Weekly Analysis", type="primary"):
            from providers.anthropic_provider import AnthropicProvider
            from providers.gemini_provider import GeminiProvider
            from providers.mlx_provider import MLXProvider
            if provider_choice.startswith("Local"):
                provider = MLXProvider()
            elif provider_choice.startswith("Gemini"):
                provider = GeminiProvider()
            else:
                provider = AnthropicProvider()
            with st.spinner("Analysing this week..."):
                try:
                    analysis = analysis_service.generate_analysis(today, provider)
                    _display_analysis(analysis)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")
    else:
        st.caption("No analysis for this week." if selected_week != today
                   else "Weekly analysis is generated on Sundays.")


def _display_analysis(analysis: dict):
    st.markdown(f"> {analysis.get('week_summary', '')}")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Weak standards**")
        for s in analysis.get("weak_standards", []):
            st.markdown(f"- {s}")
        st.markdown("**Error patterns**")
        for p in analysis.get("error_patterns", []):
            st.markdown(f"- {p}")
    with c2:
        st.markdown("**Strong standards**")
        for s in analysis.get("strong_standards", []):
            st.markdown(f"- {s}")
        st.markdown("**Recommendations**")
        for r in analysis.get("recommendations", []):
            st.markdown(f"- {r}")

    trend = analysis.get("score_trend", "")
    trend_emoji = {"improving": "📈", "declining": "📉", "stable": "➡️"}.get(trend, "")
    st.markdown(f"**Trend:** {trend_emoji} {trend}  |  **Next week focus:** {analysis.get('next_week_focus', '')} ")
    st.info(analysis.get("encouragement", ""))
