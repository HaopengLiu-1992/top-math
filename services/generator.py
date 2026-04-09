import json
from datetime import date

from providers.base import ModelProvider
from providers.anthropic_provider import AnthropicProvider
from storage import homework_store, history_store
from services.dedup_service import check_duplicates, extract_all_fingerprints
from prompts import homework_prompt
from pdf.questions_pdf import build as build_questions
from pdf.answers_pdf import build as build_answers

MAX_RETRIES = 3
INCLUDE_FORBIDDEN_IN_PROMPT = False  # set True to pass fingerprints to model (costs more tokens)


def generate(date_str: str | None = None, provider: ModelProvider | None = None) -> dict:
    today = date_str or date.today().isoformat()
    provider = provider or AnthropicProvider()

    existing = homework_store.load_questions(today)
    if existing:
        _ensure_pdfs(existing, today)
        return existing

    next_day = history_store.get_total_days() + 1
    forbidden = history_store.get_all_fingerprints()
    recent_topics = history_store.get_recent_topics(past_days=14)

    homework = _generate_with_retry(next_day, today, recent_topics, forbidden, provider)
    homework["session_type"] = "normal"
    homework["model"] = provider.name

    homework_store.save_questions(homework, today)
    homework_store.save_meta(homework_store.build_meta(homework), today)
    build_questions(homework)
    build_answers(homework)
    history_store.save_fingerprints(today, extract_all_fingerprints(homework))

    return homework


def _generate_with_retry(day: int, date_str: str, recent_topics: list,
                         forbidden: set, provider: ModelProvider) -> dict:
    system = homework_prompt.system_prompt()

    for attempt in range(1, MAX_RETRIES + 1):
        # On retries, always include forbidden fingerprints so model can avoid them
        include = INCLUDE_FORBIDDEN_IN_PROMPT or attempt > 1
        user = homework_prompt.user_prompt(day, date_str, recent_topics, forbidden,
                                           include_forbidden=include)
        print(f"  [{provider.name}] attempt {attempt}/{MAX_RETRIES}")
        raw = provider.complete(system=system, user=user)

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        try:
            homework = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  JSON error: {e}")
            continue

        dupes = check_duplicates(homework, forbidden)
        if dupes:
            print(f"  {len(dupes)} duplicate(s) found, retrying...")
            forbidden.update(dupes)
            continue

        return homework

    raise RuntimeError(f"Failed to generate homework after {MAX_RETRIES} attempts.")


def _ensure_pdfs(homework: dict, date_str: str):
    d = homework_store.pdf_dir(date_str)
    if not (d / "questions.pdf").exists() or not (d / "answers.pdf").exists():
        build_questions(homework)
        build_answers(homework)
