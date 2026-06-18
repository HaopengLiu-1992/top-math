from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from domain.daily_task import ALL_TASK_SCOPES, MATH_HOMEWORK, TASK_LABELS
from providers.provider_resolver import resolve_provider
from services import feedback_service, summary_service
from storage import daily_task_store, history_store, homework_store

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


def _build_activity_df() -> pd.DataFrame:
    rows = []
    for record in daily_task_store.list_task_records(ALL_TASK_SCOPES):
        task = record["task"]
        rows.append({
            "date": record["date"],
            "subject": record["subject"],
            "task_type": record["task_type"],
            "label": TASK_LABELS.get(record["scope"], record["scope"].key),
            "estimated_minutes": task.get("estimated_minutes"),
            "model": task.get("model", "—"),
        })

    existing = {(r["date"], r["subject"], r["task_type"]) for r in rows}
    for d in history_store.get_all_dates():
        if (d, "math", "homework") in existing:
            continue
        hw = homework_store.load_questions(d)
        if hw:
            rows.append({
                "date": d,
                "subject": "math",
                "task_type": "homework",
                "label": TASK_LABELS[MATH_HOMEWORK],
                "estimated_minutes": hw.get("estimated_minutes"),
                "model": hw.get("model", "—"),
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
    return df


def render(provider_choice: str):
    st.title("Analysis")

    activity_df = _build_activity_df()
    if activity_df.empty:
        st.info("No tasks generated yet. Go to Daily to get started.")
        return

    _render_activity(activity_df)
    st.divider()

    df = _build_df()
    if df.empty:
        return

    st.subheader("Math Analysis")
    _render_metrics(df)
    st.divider()
    _render_streak(df)
    st.divider()
    _render_daily_scores(df)
    _render_topic_coverage(df)
    _render_summary(provider_choice)

    st.subheader("All Days")
    display_df = df[["date", "day", "session_type", "score_pct", "topics"]].sort_values(
        "date", ascending=False
    ).copy()
    display_df["score_pct"] = display_df["score_pct"].apply(
        lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
    )
    st.dataframe(display_df, width="stretch")


def _render_activity(df: pd.DataFrame):
    st.subheader("Daily Activity")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tasks", len(df))
    c2.metric("Subjects", df["subject"].nunique())
    c3.metric("Task types", df["task_type"].nunique())
    total_minutes = pd.to_numeric(df["estimated_minutes"], errors="coerce").fillna(0).sum()
    c4.metric("Est. minutes", int(total_minutes) if total_minutes else "—")

    counts = df.groupby(["subject", "task_type"]).size().reset_index(name="count")
    if not counts.empty:
        fig = px.bar(counts, x="task_type", y="count", color="subject",
                     labels={"task_type": "Task type", "count": "Count"})
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, width="stretch")

    display_df = df[["date", "label", "subject", "task_type", "estimated_minutes", "model"]].sort_values(
        "date", ascending=False
    ).copy()
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


def _render_summary(provider_choice: str):
    default_start, default_end = summary_service.default_range()
    with st.container(border=True):
        st.markdown('<div class="tm-section-label">Summary</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        start_value = c1.date_input("Start date", value=date.fromisoformat(default_start))
        end_value = c2.date_input("End date", value=date.fromisoformat(default_end))
        c_generate, c_force = st.columns([2, 1])
        generate = c_generate.button("Generate Summary", type="primary")
        force = c_force.checkbox("Regenerate", value=False)

    start_date = start_value.isoformat()
    end_date = end_value.isoformat()

    if date.fromisoformat(start_date) > date.fromisoformat(end_date):
        st.error("Start date must be on or before end date.")
        return

    summary = summary_service.load_summary(start_date, end_date)

    if generate:
        provider = resolve_provider(provider_choice)
        with st.spinner("Generating summary..."):
            try:
                summary = summary_service.generate_summary(
                    start_date, end_date, provider, force=force
                )
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")
                return

    report = summary.get("feedback_report")
    analysis = summary.get("analysis")
    if not report and not analysis:
        st.caption("No summary for this range yet. Default range is the most recent week.")
        st.divider()
        return

    if report:
        _display_feedback_report(report)
    if analysis:
        _display_analysis(analysis)


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
