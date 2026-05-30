import json
from datetime import date

from domain.learning_context import LearningContext
from providers.base import ModelProvider
from providers.default_provider import get_default_provider
from storage import homework_store, history_store
from services import curriculum_service, lesson_service
from services.dedup_service import check_duplicates, extract_all_fingerprints
from prompts import homework_prompt

MAX_RETRIES = 3
INCLUDE_FORBIDDEN_IN_PROMPT = False  # set True to pass fingerprints to model (costs more tokens)


def generate(date_str: str | None = None, provider: ModelProvider | None = None,
             grade_level: int = 6, include_lesson: bool = True,
             include_hints: bool = True, target_topic_id: str | None = None,
             mode: str = "lesson_practice") -> dict:
    today = date_str or date.today().isoformat()
    provider = provider or get_default_provider()

    existing = homework_store.load_questions(today)
    if existing:
        _ensure_pdfs(existing, today)
        return existing

    next_day = history_store.get_total_days() + 1
    forbidden = history_store.get_all_fingerprints()
    recent_topics = history_store.get_recent_topics(past_days=14)
    context = LearningContext(
        grade_level=grade_level,
        mode=mode,
        include_lesson=include_lesson,
        include_hints=include_hints,
        target_topic_id=target_topic_id,
        recent_topics=recent_topics,
    )
    topic = curriculum_service.resolve_topic(context)
    cached_lesson = lesson_service.load_cached_lesson(context, topic) if include_lesson else None

    homework = _generate_with_retry(next_day, today, recent_topics, forbidden, provider,
                                    context=context, topic=topic,
                                    cached_lesson=cached_lesson)
    homework["session_type"] = "normal"
    homework["model"] = provider.name
    homework["subject"] = context.subject
    homework["grade_level"] = context.grade_level
    homework["mode"] = context.mode
    homework["target_topic"] = {
        "id": topic.id,
        "title": topic.title,
        "standard": topic.standard,
        "domain": topic.domain,
    }
    if include_lesson and cached_lesson and not homework.get("lesson"):
        homework["lesson"] = cached_lesson
    if include_lesson:
        lesson_service.cache_lesson_from_homework(homework, context, topic)

    homework_store.save_questions(homework, today)
    homework_store.save_meta(homework_store.build_meta(homework), today)
    from pdf.questions_pdf import build as build_questions
    from pdf.answers_pdf import build as build_answers
    build_questions(homework)
    build_answers(homework)
    history_store.save_fingerprints(today, extract_all_fingerprints(homework))

    return homework


def _generate_with_retry(day: int, date_str: str, recent_topics: list,
                         forbidden: set, provider: ModelProvider,
                         context: LearningContext | None = None,
                         topic=None,
                         cached_lesson: dict | None = None) -> dict:
    system = homework_prompt.system_prompt()

    for attempt in range(1, MAX_RETRIES + 1):
        # On retries, always include forbidden fingerprints so model can avoid them
        include = INCLUDE_FORBIDDEN_IN_PROMPT or attempt > 1
        user = homework_prompt.user_prompt(day, date_str, recent_topics, forbidden,
                                           include_forbidden=include,
                                           context=context,
                                           topic=topic,
                                           cached_lesson=cached_lesson)
        print(f"  [{provider.name}] attempt {attempt}/{MAX_RETRIES}")
        raw = provider.complete(system=system, user=user, max_tokens=12000)

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        try:
            homework = json.loads(raw)
            if not isinstance(homework, dict):
                raise ValueError(f"expected JSON object, got {type(homework).__name__}")
        except (json.JSONDecodeError, ValueError) as e:
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
        from pdf.questions_pdf import build as build_questions
        from pdf.answers_pdf import build as build_answers
        build_questions(homework)
        build_answers(homework)
