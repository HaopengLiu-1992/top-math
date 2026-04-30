"""
Sunday review session logic.
Collects incorrect questions from the past 7 days and generates a targeted review.
"""

import json
from datetime import date, timedelta

from providers.base import ModelProvider
from providers.anthropic_provider import AnthropicProvider
from storage import homework_store, history_store
from storage.mark_buffer import get_marks
from prompts import review_prompt
from pdf.questions_pdf import build as build_questions
from pdf.answers_pdf import build as build_answers

MAX_RETRIES = 3


def is_sunday(date_str: str | None = None) -> bool:
    d = date.fromisoformat(date_str) if date_str else date.today()
    return d.weekday() == 6


def collect_incorrect_questions(date_str: str | None = None, past_days: int = 7) -> list[dict]:
    """Return all incorrectly marked questions from the past N days."""
    today = date.fromisoformat(date_str) if date_str else date.today()
    incorrect: list[dict] = []

    for offset in range(1, past_days + 1):
        d = (today - timedelta(days=offset)).isoformat()
        hw = homework_store.load_questions(d)
        if not hw:
            continue
        meta = homework_store.load_meta(d)
        marks = get_marks(d)

        for part in hw.get("parts", {}).values():
            for q in part:
                if marks.get(q["id"]) is False:
                    incorrect.append({
                        "id": q["id"],
                        "question": q["question"],
                        "answer": q["answer"],
                        "topic": meta.get(q["id"], {}).get("topic", ""),
                        "fingerprint": q.get("fingerprint", ""),
                        "source_date": hw["date"],
                    })

    return incorrect


def generate_review(date_str: str | None = None,
                    provider: ModelProvider | None = None) -> dict | None:
    today = date_str or date.today().isoformat()
    provider = provider or AnthropicProvider()

    existing = homework_store.load_questions(today)
    if existing:
        _ensure_pdfs(existing, today)
        return existing

    incorrect = collect_incorrect_questions(today)
    if not incorrect:
        return None

    homework = _generate_with_retry(today, incorrect, provider)
    homework["session_type"] = "review"
    homework["model"] = provider.name
    homework["reviewed_topics"] = list({q["topic"] for q in incorrect if q.get("topic")})
    homework["source_incorrect_count"] = len(incorrect)

    homework_store.save_questions(homework, today)
    homework_store.save_meta(homework_store.build_meta(homework), today)
    build_questions(homework)
    build_answers(homework)

    return homework


def _generate_with_retry(date_str: str, incorrect: list[dict],
                         provider: ModelProvider) -> dict:
    system = review_prompt.system_prompt()
    user = review_prompt.user_prompt(date_str, incorrect)

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"  [Review/{provider.name}] attempt {attempt}/{MAX_RETRIES}")
        raw = provider.complete(system=system, user=user)

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        try:
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError(f"expected JSON object, got {type(result).__name__}")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  JSON error: {e}")
            continue

    raise RuntimeError(f"Failed to generate review after {MAX_RETRIES} attempts.")


def _ensure_pdfs(homework: dict, date_str: str):
    d = homework_store.pdf_dir(date_str)
    if not (d / "questions.pdf").exists() or not (d / "answers.pdf").exists():
        build_questions(homework)
        build_answers(homework)
