"""
Weekly feedback report — generated every Sunday.
A warm parent-facing report distinct from the structured skills analysis.
"""

import json
from datetime import date

from providers.base import ModelProvider
from providers.anthropic_provider import AnthropicProvider
from storage import homework_store, history_store
from services.review_service import collect_incorrect_questions
from prompts import feedback_report_prompt

MAX_RETRIES = 2
_REPORT_FILENAME = "feedback_report.json"


def report_path(date_str: str):
    from storage.homework_store import day_dir
    return day_dir(date_str) / _REPORT_FILENAME


def load_report(date_str: str) -> dict | None:
    p = report_path(date_str)
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def save_report(report: dict, date_str: str):
    p = report_path(date_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(report, f, indent=2)


def generate_report(date_str: str | None = None,
                    provider: ModelProvider | None = None) -> dict:
    today = date_str or date.today().isoformat()
    provider = provider or AnthropicProvider()

    existing = load_report(today)
    if existing:
        return existing

    weekly_logs = history_store.get_weekly_logs(today, past_days=7)
    incorrect = collect_incorrect_questions(today, past_days=7)

    report = _generate_with_retry(today, weekly_logs, incorrect, provider)
    save_report(report, today)
    return report


def _generate_with_retry(date_str: str, weekly_logs: list[dict],
                         incorrect: list[dict], provider: ModelProvider) -> dict:
    system = feedback_report_prompt.system_prompt()
    user = feedback_report_prompt.user_prompt(date_str, weekly_logs, incorrect)

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"  [FeedbackReport/{provider.name}] attempt {attempt}/{MAX_RETRIES}")
        raw = provider.complete(system=system, user=user, max_tokens=2000)

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  JSON error: {e}")
            continue

    raise RuntimeError(f"Failed to generate feedback report after {MAX_RETRIES} attempts.")
