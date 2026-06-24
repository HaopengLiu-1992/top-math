import json
from datetime import date

from providers.base import ModelProvider
from providers.default_provider import get_default_provider
from prompts import writing_prompt
from storage import writing_store


def generate(date_str: str | None = None, provider: ModelProvider | None = None,
             grade_level: int = 6, focus: str = "opinion writing",
             force: bool = False) -> dict:
    today = date_str or date.today().isoformat()
    provider = provider or get_default_provider()

    existing = writing_store.load_task(today)
    if existing and not force:
        _ensure_pdfs(existing)
        return existing

    raw = provider.complete(
        system=writing_prompt.system_prompt(),
        user=writing_prompt.user_prompt(today, grade_level, focus),
        max_tokens=7000,
    )
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    task = json.loads(raw)
    task["date"] = today
    task["subject"] = "english"
    task["task_type"] = "writing"
    task["grade_level"] = grade_level
    task["model"] = provider.name
    _normalize_task(task)

    writing_store.save_task(today, task)
    writing_store.save_meta(today, writing_store.build_meta(task))
    _ensure_pdfs(task)
    return task


def _ensure_pdfs(task: dict):
    from pdf.writing_pdf import build_answers, build_writing
    date_str = task["date"]
    pdf_d = writing_store.pdf_dir(date_str)
    if not (pdf_d / "writing.pdf").exists():
        build_writing(task)
    if not (pdf_d / "answers.pdf").exists():
        build_answers(task)


def _normalize_task(task: dict):
    task.setdefault("title", "Opinion Writing Memory Set")
    task.setdefault("estimated_minutes", 20)
    task.setdefault("opinion", {})
    examples = task.setdefault("examples", [])
    for idx, item in enumerate(examples, 1):
        item.setdefault("id", f"example_{idx:03d}")
        item.setdefault("memorize_line", item.get("example", ""))

    practice = task.setdefault("practice", {})
    checks = [{
        "id": "opinion",
        "prompt": "Say the opinion sentence from memory.",
        "answer": task["opinion"].get("memorize_line") or task["opinion"].get("claim", ""),
    }]
    checks.extend({
        "id": item.get("id", f"example_{idx:03d}"),
        "prompt": f"Say example {idx} from memory.",
        "answer": item.get("memorize_line", ""),
    } for idx, item in enumerate(examples, 1))
    practice["recitation_check"] = checks
