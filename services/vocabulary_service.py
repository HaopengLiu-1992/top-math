import json
from datetime import date

from providers.base import ModelProvider
from providers.default_provider import get_default_provider
from prompts import vocabulary_prompt
from storage import vocabulary_store

NEW_WORD_COUNT = 15
REVIEW_WORD_COUNT = 5


def generate(date_str: str | None = None, provider: ModelProvider | None = None,
             grade_level: int = 6, force: bool = False) -> dict:
    today = date_str or date.today().isoformat()
    provider = provider or get_default_provider()

    existing = vocabulary_store.load_task(today)
    if existing and not force:
        _ensure_pdfs(existing)
        return existing

    new_words, review_words = _select_words(today)
    raw = provider.complete(
        system=vocabulary_prompt.system_prompt(),
        user=vocabulary_prompt.user_prompt(today, grade_level, new_words, review_words),
        max_tokens=8000,
    )
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    task = json.loads(raw)
    task["date"] = today
    task["subject"] = "english"
    task["task_type"] = "vocabulary"
    task["grade_level"] = grade_level
    task["model"] = provider.name

    vocabulary_store.save_task(today, task)
    vocabulary_store.save_meta(today, vocabulary_store.build_meta(task))
    _ensure_pdfs(task)
    return task


def _select_words(date_str: str) -> tuple[list[dict], list[dict]]:
    bank = vocabulary_store.load_word_bank()
    seen = _seen_words()
    review_words = [w for w in bank if w["word"] in seen][:REVIEW_WORD_COUNT]
    new_needed = NEW_WORD_COUNT + max(0, REVIEW_WORD_COUNT - len(review_words))
    new_words = [w for w in bank if w["word"] not in seen][:new_needed]
    if len(new_words) < new_needed:
        new_words.extend([w for w in bank if w not in new_words and w not in review_words][:new_needed - len(new_words)])
    return new_words, review_words


def _seen_words() -> set[str]:
    seen = set()
    for date_str in vocabulary_store.list_dates():
        meta = vocabulary_store.load_meta(date_str)
        seen.update(meta.keys())
    return seen


def _ensure_pdfs(task: dict):
    from pdf.vocabulary_pdf import build_answers, build_vocabulary
    date_str = task["date"]
    pdf_d = vocabulary_store.pdf_dir(date_str)
    if not (pdf_d / "vocabulary.pdf").exists():
        build_vocabulary(task)
    if not (pdf_d / "answers.pdf").exists():
        build_answers(task)
