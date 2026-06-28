import json
from datetime import date

from domain.daily_task import ENGLISH_READING, SCIENCE_READING, TaskScope
from providers.base import ModelProvider
from providers.default_provider import get_default_provider
from prompts import reading_prompt
from services import reading_guardrail
from storage import reading_store

MAX_GUARDRAIL_ATTEMPTS = 2


def generate(scope: TaskScope, date_str: str | None = None,
             provider: ModelProvider | None = None, grade_level: int = 6,
             focus: str = "academic reading", force: bool = False) -> dict:
    today = date_str or date.today().isoformat()
    provider = provider or get_default_provider()

    existing = reading_store.load_task(scope, today)
    if existing and not force:
        _ensure_pdfs(scope, existing)
        return existing

    plan = reading_guardrail.prepare(scope, today, grade_level, focus)
    task = _generate_with_guardrail(scope, today, provider, grade_level, focus, plan)
    task["date"] = today
    task["subject"] = scope.subject
    task["task_type"] = scope.task_type
    task["grade_level"] = grade_level
    task["model"] = provider.name
    reading_guardrail.commit(scope, today, task, plan)

    reading_store.save_task(scope, today, task)
    reading_store.save_meta(scope, today, reading_store.build_meta(task))
    _ensure_pdfs(scope, task)
    return task


def _generate_with_guardrail(scope: TaskScope, today: str, provider: ModelProvider,
                             grade_level: int, focus: str,
                             plan: reading_guardrail.ReadingPlan) -> dict:
    last_errors: list[str] = []
    for attempt in range(MAX_GUARDRAIL_ATTEMPTS):
        user_prompt = reading_prompt.user_prompt(
            today,
            grade_level,
            scope.subject,
            focus,
            guardrail={
                **plan.as_prompt_context(),
                "validation_retry": attempt,
                "previous_errors": last_errors,
            },
        )
        raw = provider.complete(
            system=reading_prompt.system_prompt(),
            user=user_prompt,
            max_tokens=9000,
        )
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        task = json.loads(raw)
        last_errors = reading_guardrail.validate(scope, task, plan)
        if not last_errors:
            return task
    raise ValueError(f"Reading guardrail rejected generated task: {last_errors}")


def _ensure_pdfs(scope: TaskScope, task: dict):
    from pdf.reading_pdf import build_answers, build_reading
    date_str = task["date"]
    pdf_d = reading_store.pdf_dir(scope, date_str)
    if not (pdf_d / "reading.pdf").exists():
        build_reading(scope, task)
    if not (pdf_d / "answers.pdf").exists():
        build_answers(scope, task)


def default_focus(scope: TaskScope) -> str:
    if scope == SCIENCE_READING:
        return "science vocabulary, evidence, cause and effect"
    if scope == ENGLISH_READING:
        return "main idea, inference, vocabulary in context"
    return "academic reading"
