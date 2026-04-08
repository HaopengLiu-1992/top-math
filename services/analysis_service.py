"""
Weekly skills analysis — runs on Sundays.
Produces a structured JSON report stored as output/raw/YYYY/MM/DD/analysis.json.
"""

import json
from datetime import date

from providers.base import ModelProvider
from providers.anthropic_provider import AnthropicProvider
from storage import homework_store, history_store
from services.review_service import collect_incorrect_questions
from prompts import analysis_prompt

MAX_RETRIES = 2


def generate_analysis(date_str: str | None = None,
                      provider: ModelProvider | None = None) -> dict:
    today = date_str or date.today().isoformat()
    provider = provider or AnthropicProvider()

    existing = homework_store.load_analysis(today)
    if existing:
        return existing

    weekly_logs = history_store.get_weekly_logs(today, past_days=7)
    incorrect = collect_incorrect_questions(today, past_days=7)

    analysis = _generate_with_retry(today, weekly_logs, incorrect, provider)
    analysis["generated_date"] = today

    homework_store.save_analysis(analysis, today)
    return analysis


def load_analysis(date_str: str) -> dict | None:
    return homework_store.load_analysis(date_str)


def _generate_with_retry(date_str: str, weekly_logs: list[dict],
                         incorrect: list[dict], provider: ModelProvider) -> dict:
    system = analysis_prompt.system_prompt()
    user = analysis_prompt.user_prompt(date_str, weekly_logs, incorrect)

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"  [Analysis/{provider.name}] attempt {attempt}/{MAX_RETRIES}")
        raw = provider.complete(system=system, user=user, max_tokens=2000)

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  JSON error: {e}")
            continue

    raise RuntimeError(f"Failed to generate analysis after {MAX_RETRIES} attempts.")
