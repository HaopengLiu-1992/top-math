import json
from datetime import date

from providers.base import ModelProvider
from providers.default_provider import get_default_provider
from prompts import vocabulary_prompt
from storage import vocabulary_store

NEW_WORD_COUNT = 15
REVIEW_WORD_COUNT = 5
STAGE_ORDER = ["cn_middle_school", "cn_high_school", "cn_high_school_extension"]


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
    index = vocabulary_store.load_word_index()
    by_word = {item["word"]: item for item in bank}
    seen = _seen_words()

    review_words = _select_review_words(bank, seen)
    new_needed = NEW_WORD_COUNT + max(0, REVIEW_WORD_COUNT - len(review_words))
    new_words = _select_new_words(index, by_word, seen, new_needed)
    if len(new_words) < new_needed:
        selected = {w["word"] for w in new_words} | {w["word"] for w in review_words}
        new_words.extend(
            w for w in bank
            if w["word"] not in selected and w["word"] not in seen
        )
        new_words = new_words[:new_needed]
    return new_words, review_words


def _select_review_words(bank: list[dict], seen: set[str]) -> list[dict]:
    if not seen:
        return []
    return [w for w in bank if w["word"] in seen][:REVIEW_WORD_COUNT]


def _select_new_words(index: dict, by_word: dict[str, dict], seen: set[str], count: int) -> list[dict]:
    selected: list[dict] = []
    selected_words: set[str] = set()
    for word in index.get("learning_sequence", []):
        if word not in by_word or word in seen or word in selected_words:
            continue
        selected.append(by_word[word])
        selected_words.add(word)
        if len(selected) == count:
            return selected

    category_plan = index.get("daily_category_plan", index.get("category_order", []))
    by_stage_category = index.get("by_stage_category", {})

    for stage in index.get("stage_order", STAGE_ORDER):
        # First pass: category-balanced basics.
        for category in category_plan:
            word = _first_available_word(
                by_stage_category.get(stage, {}).get(category, []),
                by_word,
                seen,
                selected_words,
            )
            if word:
                selected.append(by_word[word])
                selected_words.add(word)
                if len(selected) == count:
                    return selected

        # Second pass: fill from the same stage before moving harder.
        for words in by_stage_category.get(stage, {}).values():
            for word in words:
                if word not in by_word or word in seen or word in selected_words:
                    continue
                selected.append(by_word[word])
                selected_words.add(word)
                if len(selected) == count:
                    return selected

    return selected


def _first_available_word(words: list[str], by_word: dict[str, dict],
                          seen: set[str], selected: set[str]) -> str | None:
    for word in words:
        if word in by_word and word not in seen and word not in selected:
            return word
    return None


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
