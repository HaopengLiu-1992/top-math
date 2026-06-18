import json
from datetime import date

from domain.daily_task import ENGLISH_READING, SCIENCE_READING, TaskScope
from providers.base import ModelProvider
from providers.default_provider import get_default_provider
from prompts import reading_prompt
from storage import reading_store


def generate(scope: TaskScope, date_str: str | None = None,
             provider: ModelProvider | None = None, grade_level: int = 6,
             focus: str = "academic reading", force: bool = False) -> dict:
    today = date_str or date.today().isoformat()
    provider = provider or get_default_provider()

    existing = reading_store.load_task(scope, today)
    if existing and not force:
        _ensure_pdfs(scope, existing)
        return existing

    raw = provider.complete(
        system=reading_prompt.system_prompt(),
        user=reading_prompt.user_prompt(today, grade_level, scope.subject, focus),
        max_tokens=9000,
    )
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    task = json.loads(raw)
    task["date"] = today
    task["subject"] = scope.subject
    task["task_type"] = scope.task_type
    task["grade_level"] = grade_level
    task["model"] = provider.name

    reading_store.save_task(scope, today, task)
    reading_store.save_meta(scope, today, reading_store.build_meta(task))
    _ensure_pdfs(scope, task)
    return task


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
