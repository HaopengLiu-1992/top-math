from datetime import date, timedelta

from providers.base import ModelProvider
from providers.default_provider import get_default_provider
from services import analysis_service, feedback_report_service
from storage import history_store, homework_store, mark_buffer, summary_store

DEFAULT_SUMMARY_DAYS = 7


def default_range(end_date: str | None = None,
                  days: int = DEFAULT_SUMMARY_DAYS) -> tuple[str, str]:
    end = date.fromisoformat(end_date) if end_date else date.today()
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def load_summary(start_date: str, end_date: str) -> dict:
    return {
        "analysis": summary_store.load_analysis(start_date, end_date),
        "feedback_report": summary_store.load_feedback_report(start_date, end_date),
    }


def generate_summary(start_date: str, end_date: str,
                     provider: ModelProvider | None = None,
                     force: bool = False) -> dict:
    provider = provider or get_default_provider()
    existing = load_summary(start_date, end_date)
    if not force and existing["analysis"] and existing["feedback_report"]:
        return existing

    logs = history_store.get_logs_for_range(start_date, end_date)
    incorrect = collect_incorrect_questions_for_range(start_date, end_date)

    analysis = existing["analysis"]
    if force or analysis is None:
        analysis = analysis_service.generate_analysis_from_data(
            start_date, end_date, logs, incorrect, provider
        )
        summary_store.save_analysis(analysis, start_date, end_date)

    report = existing["feedback_report"]
    if force or report is None:
        report = feedback_report_service.generate_report_from_data(
            start_date, end_date, logs, incorrect, provider
        )
        summary_store.save_feedback_report(report, start_date, end_date)

    return {
        "analysis": analysis,
        "feedback_report": report,
    }


def collect_incorrect_questions_for_range(start_date: str, end_date: str) -> list[dict]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if start > end:
        raise ValueError("start_date must be on or before end_date")

    incorrect: list[dict] = []
    current = start
    while current <= end:
        date_str = current.isoformat()
        hw = homework_store.load_questions(date_str)
        if hw:
            meta = homework_store.load_meta(date_str)
            marks = mark_buffer.get_marks(date_str)
            for part in hw.get("parts", {}).values():
                for q in part:
                    if marks.get(q["id"]) is False:
                        incorrect.append({
                            "id": q["id"],
                            "question": q["question"],
                            "answer": q["answer"],
                            "topic": meta.get(q["id"], {}).get("topic", ""),
                            "fingerprint": q.get("fingerprint", ""),
                            "source_date": date_str,
                        })
        current += timedelta(days=1)
    return incorrect
