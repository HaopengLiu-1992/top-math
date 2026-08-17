import json
from datetime import date, timedelta

from providers.base import ModelProvider
from providers.default_provider import get_default_provider
from prompts import vocabulary_prompt
from storage import vocabulary_store

NEW_WORD_COUNT = 15
REVIEW_WORD_COUNT = 5
MAX_GENERATION_RETRIES = 2
STAGE_ORDER = ["cn_middle_school", "cn_high_school", "cn_high_school_extension"]
TRUSTED_SOURCES = {"curated_math_science_core"}
TEACHABLE_CATEGORIES = {
    "math_operations",
    "word_problem_signals",
    "fractions_decimals",
    "geometry_measurement",
    "data_statistics",
    "academic_verbs",
    "science_process",
    "life_science",
    "physical_science",
    "earth_science",
    "general_academic",
    "math",
    "science",
}


class VocabularySelectionError(RuntimeError):
    """The local vocabulary catalog cannot produce a safe task."""


class VocabularyGenerationError(RuntimeError):
    """The provider returned a task that did not match the local selection."""


def generate(date_str: str | None = None, provider: ModelProvider | None = None,
             grade_level: int = 6, personal_prompt: str = "",
             force: bool = False) -> dict:
    today = date_str or date.today().isoformat()
    provider = provider or get_default_provider()

    existing = vocabulary_store.load_task(today)
    if existing and not force:
        _ensure_pdfs(existing)
        return existing

    new_words, review_words = _select_words(today, grade_level=grade_level)
    if not new_words and not review_words:
        raise VocabularySelectionError(
            "No unused approved vocabulary words are available. "
            "Expand or enrich the local vocabulary catalog before generating another task."
        )

    task = None
    last_error = "unknown vocabulary generation error"
    for _ in range(MAX_GENERATION_RETRIES):
        raw = provider.complete(
            system=vocabulary_prompt.system_prompt(),
            user=vocabulary_prompt.user_prompt(
                today, grade_level, new_words, review_words, personal_prompt=personal_prompt
            ),
            max_tokens=16000,
        )
        try:
            task = _normalize_generated_task(
                _parse_json_response(raw),
                new_words,
                review_words,
            )
            break
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)

    if task is None:
        raise VocabularyGenerationError(
            f"Vocabulary generation did not match the selected words: {last_error}"
        )

    task["date"] = today
    task["subject"] = "english"
    task["task_type"] = "vocabulary"
    task["grade_level"] = grade_level
    task["model"] = provider.name
    task["personal_prompt"] = personal_prompt.strip()

    vocabulary_store.save_task(today, task)
    vocabulary_store.save_meta(today, vocabulary_store.build_meta(task))
    _ensure_pdfs(task)
    return task


def _select_words(date_str: str, grade_level: int = 6) -> tuple[list[dict], list[dict]]:
    bank = vocabulary_store.load_word_bank()
    index = vocabulary_store.load_word_index()
    by_word = {item["word"]: item for item in bank}
    seen = _seen_words(exclude_date=date_str)
    history = _word_history(exclude_date=date_str)

    review_words = _select_review_words(bank, seen, history, date_str)
    new_needed = NEW_WORD_COUNT + max(0, REVIEW_WORD_COUNT - len(review_words))
    new_words = _select_new_words(index, by_word, seen, new_needed, grade_level=grade_level)
    return new_words, review_words


def _select_review_words(bank: list[dict], seen: set[str], history: dict | None = None,
                         date_str: str | None = None) -> list[dict]:
    if not seen:
        return []
    history = history or {}
    today = date.fromisoformat(date_str) if date_str else None
    candidates = [w for w in bank if w["word"] in seen]
    candidates.sort(key=lambda item: _review_sort_key(item["word"], history, today))
    return candidates[:REVIEW_WORD_COUNT]


def _review_sort_key(word: str, history: dict, today: date | None) -> tuple:
    record = history.get(word, {})
    known = record.get("known")
    status_rank = 0 if known is False else 1 if known is None else 2
    times_wrong = int(record.get("times_wrong", 0) or 0)
    times_seen = max(int(record.get("times_seen", 1) or 1), 1)
    last_seen_text = record.get("last_seen", "")
    try:
        last_seen = date.fromisoformat(last_seen_text)
    except (TypeError, ValueError):
        last_seen = date.min

    interval_days = 1 if known is False else min(30, 2 ** min(times_seen - 1, 4))
    due_rank = 0 if today and last_seen + timedelta(days=interval_days) <= today else 1
    return (status_rank, due_rank, -times_wrong, last_seen, times_seen, word)


def _select_new_words(index: dict, by_word: dict[str, dict], seen: set[str], count: int,
                      grade_level: int = 6) -> list[dict]:
    selected: list[dict] = []
    selected_words: set[str] = set()
    for word in index.get("learning_sequence", []):
        if (
            word not in by_word
            or word in seen
            or word in selected_words
            or not _is_teachable_word(by_word[word])
            or not _is_grade_appropriate(by_word[word], grade_level)
        ):
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
                grade_level,
            )
            if word:
                selected.append(by_word[word])
                selected_words.add(word)
                if len(selected) == count:
                    return selected

        # Second pass: fill from the same stage before moving harder.
        for words in by_stage_category.get(stage, {}).values():
            for word in words:
                if (
                    word not in by_word
                    or word in seen
                    or word in selected_words
                    or not _is_teachable_word(by_word[word])
                    or not _is_grade_appropriate(by_word[word], grade_level)
                ):
                    continue
                selected.append(by_word[word])
                selected_words.add(word)
                if len(selected) == count:
                    return selected

    return selected


def _first_available_word(words: list[str], by_word: dict[str, dict],
                          seen: set[str], selected: set[str], grade_level: int = 6) -> str | None:
    for word in words:
        if (
            word in by_word
            and word not in seen
            and word not in selected
            and _is_teachable_word(by_word[word])
            and _is_grade_appropriate(by_word[word], grade_level)
        ):
            return word
    return None


def _is_teachable_word(item: dict) -> bool:
    word = item.get("word", "")
    if item.get("source") in TRUSTED_SOURCES:
        return True
    if item.get("category") not in TEACHABLE_CATEGORIES:
        return False
    if not item.get("definition"):
        return False
    if len(word) < 3 or len(word) > 18:
        return False
    if any(ch.isdigit() for ch in word):
        return False
    return True


def _is_grade_appropriate(item: dict, grade_level: int) -> bool:
    """Apply the catalog's grade band without rejecting legacy entries."""
    minimum = item.get("grade_min")
    maximum = item.get("grade_max")
    if minimum is None or maximum is None:
        return True
    try:
        return int(minimum) <= int(grade_level) <= int(maximum)
    except (TypeError, ValueError):
        return False


def _seen_words(exclude_date: str | None = None) -> set[str]:
    return set(_word_history(exclude_date=exclude_date))


def _word_history(exclude_date: str | None = None) -> dict[str, dict]:
    """Rebuild word-level learning state from the existing per-day metadata."""
    history: dict[str, dict] = {}
    for date_str in vocabulary_store.list_dates():
        if date_str == exclude_date:
            continue
        meta = vocabulary_store.load_meta(date_str)
        for word, data in meta.items():
            record = history.setdefault(
                word,
                {
                    "last_seen": date_str,
                    "times_seen": 0,
                    "times_wrong": 0,
                    "known": None,
                },
            )
            record["times_seen"] += 1
            mark = data.get("correct", data.get("known"))
            if mark is False:
                record["times_wrong"] += 1
            if date_str >= record["last_seen"]:
                record["last_seen"] = date_str
                record["known"] = mark
    return history


def _parse_json_response(raw: str) -> dict:
    if not isinstance(raw, str):
        raise TypeError("provider response was not text")
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("\n", 1)
        if len(parts) != 2:
            raise ValueError("provider code fence is malformed")
        raw = parts[1].rsplit("```", 1)[0].strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("provider response must be a JSON object")
    return parsed


def _normalize_generated_task(task: dict, new_words: list[dict], review_words: list[dict]) -> dict:
    """Accept provider-authored practice text only for locally selected words."""
    items = task.get("words")
    if not isinstance(items, list):
        raise ValueError("response.words must be a list")

    selected = new_words + review_words
    selected_words = [item["word"] for item in selected]
    selected_set = set(selected_words)
    review_set = {item["word"] for item in review_words}
    if any(not isinstance(item, dict) or not isinstance(item.get("word"), str) for item in items):
        raise ValueError("response.words must contain objects with string word fields")
    actual_words = [item["word"] for item in items]
    actual_set = set(actual_words)

    if len(actual_words) != len(actual_set):
        raise ValueError("response.words contains duplicate words")
    missing = selected_set - actual_set
    extra = actual_set - selected_set
    if missing or extra or len(actual_words) != len(selected_words):
        details = []
        if missing:
            details.append(f"missing={sorted(missing)}")
        if extra:
            details.append(f"extra={sorted(extra)}")
        raise ValueError("response.words does not match local selection: " + ", ".join(details))

    by_word = {item["word"]: item for item in items}
    normalized = []
    for selected_item in selected:
        word = selected_item["word"]
        item = dict(by_word[word])
        item["word"] = word
        item["category"] = selected_item.get("category", item.get("category", ""))
        item["is_review"] = word in review_set
        for field in ("cn_stage", "us_band"):
            if selected_item.get(field):
                item[field] = selected_item[field]
        normalized.append(item)

    task["words"] = normalized
    return task


def _ensure_pdfs(task: dict):
    from pdf.vocabulary_pdf import build_answers, build_vocabulary
    date_str = task["date"]
    pdf_d = vocabulary_store.pdf_dir(date_str)
    if not (pdf_d / "vocabulary.pdf").exists():
        build_vocabulary(task)
    if not (pdf_d / "answers.pdf").exists():
        build_answers(task)
