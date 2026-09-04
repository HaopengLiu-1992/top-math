import json
import re
from collections import Counter
from datetime import date, timedelta
from difflib import SequenceMatcher

from providers.base import ModelProvider
from providers.default_provider import get_default_provider
from prompts import writing_prompt
from storage import reading_store, vocabulary_store, writing_store
from domain.daily_task import ENGLISH_READING

MAX_GENERATION_RETRIES = 3
SIMILARITY_THRESHOLD = 0.86
EXAMPLE_TYPES = [
    "personal_experience",
    "math_science_application",
    "reading_evidence",
    "school_observation",
    "cause_and_effect",
    "comparison",
]
WRITING_MODES = ("summary", "opinion", "text_based_response")
MODE_LABELS = {
    "summary": "Summary",
    "opinion": "Opinion / Argument",
    "text_based_response": "Text-Based Response",
}
FALLBACK_FOCUS_WORDS = [
    {"word": "evidence", "meaning": "information that supports an idea", "chinese": "证据"},
    {"word": "reason", "meaning": "a cause or explanation", "chinese": "理由"},
    {"word": "explain", "meaning": "to make an idea clear", "chinese": "解释"},
    {"word": "result", "meaning": "what happens because of something", "chinese": "结果"},
    {"word": "support", "meaning": "to provide evidence for an idea", "chinese": "支持"},
]


class WritingGenerationError(RuntimeError):
    """The provider could not produce a non-repetitive writing task."""


def generate(date_str: str | None = None, provider: ModelProvider | None = None,
             grade_level: int = 6,
             focus: str = "academic writing: answer, evidence, explanation, and revision",
             force: bool = False) -> dict:
    today = date_str or date.today().isoformat()
    provider = provider or get_default_provider()

    existing = writing_store.load_task(today)
    if existing and not force:
        _ensure_pdfs(existing)
        return existing

    history = _recent_history(today)
    context = _writing_context(today)
    plan = _choose_example_plan(today, history)
    history_context = _history_context(history)
    task = None
    last_error = "unknown writing generation error"
    for attempt in range(MAX_GENERATION_RETRIES):
        raw = provider.complete(
            system=writing_prompt.system_prompt(),
            user=writing_prompt.user_prompt(
                today,
                grade_level,
                focus,
                plan=plan,
                history=history_context,
                feedback=last_error if attempt else "",
                writing_mode=context["writing_mode"],
                focus_words=context["focus_words"],
                source_context=context["source"],
            ),
            max_tokens=7000,
        )
        try:
            task = _parse_json_response(raw)
            enforce_new_fields = any(
                key in task for key in ("writing_mode", "focus_words", "source", "writing_prompt")
            )
            _normalize_task(task, context=context)
            errors = _validate_task(
                task,
                history_context,
                plan,
                writing_mode=context["writing_mode"],
                focus_words=context["focus_words"],
                enforce_new_fields=enforce_new_fields,
            )
            if errors:
                raise ValueError("; ".join(errors))
            break
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)

    if task is None:
        raise WritingGenerationError(
            f"Writing generation did not pass the repetition guardrail: {last_error}"
        )

    task["date"] = today
    task["subject"] = "english"
    task["task_type"] = "writing"
    task["grade_level"] = grade_level
    task["focus"] = focus
    task["writing_mode"] = context["writing_mode"]
    task["mode_label"] = MODE_LABELS[context["writing_mode"]]
    task["focus_words"] = context["focus_words"]
    task["model"] = provider.name
    task["writing_guardrail"] = {
        "history_days": 30,
        "example_type_plan": [item["type"] for item in plan],
        "writing_mode": context["writing_mode"],
        "focus_words": [item["word"] for item in context["focus_words"]],
    }

    writing_store.save_task(today, task)
    writing_store.save_meta(today, writing_store.build_meta(task))
    _ensure_pdfs(task)
    return task


def _writing_context(date_str: str) -> dict:
    """Build a small bridge from vocabulary/reading into the writing task."""
    current_vocab = vocabulary_store.load_task(date_str) or {}
    focus_words = []
    for item in current_vocab.get("words", []):
        word = (item.get("word") or "").strip()
        if not word or any(existing["word"] == word for existing in focus_words):
            continue
        focus_words.append({
            "word": word,
            "meaning": item.get("definition", ""),
            "chinese": item.get("chinese", ""),
        })
        if len(focus_words) == 5:
            break
    if len(focus_words) < 5:
        used = {item["word"] for item in focus_words}
        focus_words.extend(item for item in FALLBACK_FOCUS_WORDS if item["word"] not in used)
        focus_words = focus_words[:5]

    reading_task = reading_store.load_task(ENGLISH_READING, date_str) or {}
    passage = reading_task.get("passage") or {}
    source = {
        "title": passage.get("title", ""),
        "text": passage.get("text", ""),
    }
    day_number = date.fromisoformat(date_str).toordinal()
    return {
        "writing_mode": WRITING_MODES[day_number % len(WRITING_MODES)],
        "focus_words": focus_words,
        "source": source,
    }


def _parse_json_response(raw: str) -> dict:
    if not isinstance(raw, str):
        raise TypeError("provider response was not text")
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("\n", 1)
        if len(parts) != 2:
            raise ValueError("provider code fence is malformed")
        raw = parts[1].rsplit("```", 1)[0].strip()
    task = json.loads(raw)
    if not isinstance(task, dict):
        raise ValueError("provider response must be a JSON object")
    return task


def _recent_history(date_str: str, days: int = 30) -> list[dict]:
    today = date.fromisoformat(date_str)
    first_day = today - timedelta(days=days)
    records = []
    for history_date in sorted(writing_store.list_dates(), reverse=True):
        try:
            parsed_date = date.fromisoformat(history_date)
        except (TypeError, ValueError):
            continue
        if parsed_date < first_day or parsed_date > today:
            continue
        task = writing_store.load_task(history_date) or {}
        opinion = task.get("opinion") or {}
        examples = []
        for item in task.get("examples") or []:
            if not isinstance(item, dict):
                continue
            line = item.get("memorize_line") or item.get("example") or ""
            if line:
                examples.append({
                    "type": item.get("type", ""),
                    "line": line,
                })
        opinion_line = opinion.get("memorize_line") or opinion.get("claim") or ""
        records.append({
            "date": history_date,
            "opinion": opinion_line,
            "examples": examples,
        })
    return records


def _history_context(records: list[dict]) -> dict:
    opinions = _unique([record.get("opinion", "") for record in records])[:8]
    examples = _unique([
        item.get("line", "")
        for record in records
        for item in record.get("examples", [])
    ])[:12]
    starters = _unique([
        _starter_signature(item.get("line", ""))
        for record in records
        for item in record.get("examples", [])
    ])[:12]
    types = Counter(
        item.get("type", "")
        for record in records
        for item in record.get("examples", [])
        if item.get("type")
    )
    return {
        "avoid_opinions": opinions,
        "avoid_examples": examples,
        "avoid_starters": starters,
        "recent_type_counts": dict(types),
    }


def _choose_example_plan(date_str: str, records: list[dict]) -> list[dict]:
    context = _history_context(records)
    counts = Counter(context.get("recent_type_counts", {}))
    day_offset = date.fromisoformat(date_str).toordinal()

    # Keep one math/science slot every day, then rotate the other two slots
    # toward the least-used types in the recent window.
    selected = ["math_science_application"]
    for position in range(2):
        candidates = [item for item in EXAMPLE_TYPES if item not in selected]
        candidates.sort(
            key=lambda item: (
                counts[item],
                (EXAMPLE_TYPES.index(item) + day_offset + position) % len(EXAMPLE_TYPES),
            )
        )
        selected.append(candidates[0])
        counts[candidates[0]] += 1

    return [
        {"position": index, "type": item}
        for index, item in enumerate(selected, 1)
    ]


def _validate_task(task: dict, history: dict, plan: list[dict],
                   writing_mode: str | None = None,
                   focus_words: list[dict] | None = None,
                   enforce_new_fields: bool = False) -> list[str]:
    errors: list[str] = []
    actual_mode = task.get("writing_mode", "opinion")
    if enforce_new_fields and writing_mode and actual_mode != writing_mode:
        errors.append(f"writing mode must be {writing_mode}")
    if enforce_new_fields and actual_mode not in WRITING_MODES:
        errors.append(f"unsupported writing mode: {actual_mode}")

    practice = task.get("practice") or {}
    prompt = task.get("writing_prompt") or (
        practice.get("rewrite_task", "") if isinstance(practice, dict) else ""
    )
    if enforce_new_fields and not prompt:
        errors.append("missing writing prompt")

    if enforce_new_fields and focus_words:
        actual_focus_words = task.get("focus_words") or []
        expected_words = [item["word"] for item in focus_words]
        received_words = [item.get("word", "") for item in actual_focus_words if isinstance(item, dict)]
        if received_words != expected_words:
            errors.append("focus words must match the selected vocabulary words")
        word_sentences = practice.get("word_sentences") if isinstance(practice, dict) else []
        word_sentences = word_sentences or []
        sentence_words = [item.get("word", "") for item in word_sentences if isinstance(item, dict)]
        if sentence_words != expected_words:
            errors.append("writing practice must include one sentence exercise per focus word")

    if enforce_new_fields and actual_mode in {"summary", "text_based_response"}:
        source = task.get("source") or {}
        if not source.get("text"):
            errors.append("summary and text-based response tasks need a source passage")

    opinion = task.get("opinion") or {}
    opinion_line = opinion.get("memorize_line") or opinion.get("claim") or ""
    examples = task.get("examples")
    expected_types = [item["type"] for item in plan]

    if not opinion_line:
        errors.append("missing opinion sentence")
    if not isinstance(examples, list) or len(examples) != 3:
        errors.append("expected exactly 3 examples")
        return errors

    actual_types = [item.get("type") if isinstance(item, dict) else "" for item in examples]
    if actual_types != expected_types:
        errors.append(f"example types must be {expected_types}")

    lines = []
    starter_signatures = []
    for index, item in enumerate(examples, 1):
        if not isinstance(item, dict):
            errors.append(f"example {index} is not an object")
            continue
        line = item.get("memorize_line") or item.get("example") or ""
        if not line:
            errors.append(f"example {index} is missing a sentence")
            continue
        lines.append(line)
        starter_signatures.append(_starter_signature(line))

    if len(set(_normalize(line) for line in lines)) != len(lines):
        errors.append("examples contain duplicate sentences")
    if len(set(starter_signatures)) != len(starter_signatures):
        errors.append("examples reuse the same sentence starter")

    recent_opinions = history.get("avoid_opinions", [])
    if any(_similarity(opinion_line, previous) >= SIMILARITY_THRESHOLD
           for previous in recent_opinions):
        errors.append("opinion sentence is too similar to recent writing")

    recent_examples = history.get("avoid_examples", [])
    if any(_similarity(line, previous) >= SIMILARITY_THRESHOLD for line in lines for previous in recent_examples):
        errors.append("example sentence is too similar to recent writing")

    recent_starters = set(history.get("avoid_starters", []))
    if any(signature in recent_starters for signature in starter_signatures):
        errors.append("example sentence starter repeats recent writing")
    return errors


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", value.lower()).strip()


def _starter_signature(value: str) -> str:
    words = _normalize(value).split()
    return " ".join(words[:3])


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        value = value.strip()
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _ensure_pdfs(task: dict):
    from pdf.writing_pdf import build_answers, build_writing
    date_str = task["date"]
    pdf_d = writing_store.pdf_dir(date_str)
    if not (pdf_d / "writing.pdf").exists():
        build_writing(task)
    if not (pdf_d / "answers.pdf").exists():
        build_answers(task)


def _normalize_task(task: dict, context: dict | None = None):
    if not isinstance(task, dict):
        raise ValueError("writing task must be an object")
    task.setdefault("title", "Daily Writing Lab — Opinion / Argument")
    task.setdefault("estimated_minutes", 20)
    context = context or {}
    task.setdefault("writing_mode", context.get("writing_mode", "opinion"))
    task.setdefault("mode_label", MODE_LABELS.get(task["writing_mode"], "Opinion / Argument"))
    task.setdefault("time_plan", [
        {"minutes": 5, "activity": "Use each focus word in an original sentence."},
        {"minutes": 10, "activity": "Write a three-paragraph, 8-12 sentence first draft."},
        {"minutes": 5, "activity": "Revise one sentence and complete the checklist."},
    ])
    if not isinstance(task["time_plan"], list):
        raise ValueError("writing time_plan must be a list")
    task.setdefault("source", context.get("source", {}))
    if not isinstance(task["source"], dict):
        raise ValueError("writing source must be an object")
    task.setdefault("writing_prompt", "Write a short essay in three paragraphs and 8-12 sentences using Answer, Evidence, and Explain.")
    task.setdefault("paragraph_plan", [
        {"label": "Introduction", "purpose": "Answer the prompt and state the main idea."},
        {"label": "Body", "purpose": "Give evidence or a specific example and explain it."},
        {"label": "Conclusion", "purpose": "Restate the main idea and close the essay."},
    ])
    if not isinstance(task["paragraph_plan"], list):
        raise ValueError("writing paragraph_plan must be a list")
    task.setdefault("structure", [
        {"label": "Answer", "instruction": "Answer the prompt directly.", "frame": "I think ___ because ___ ."},
        {"label": "Evidence", "instruction": "Give a detail, example, or reason.", "frame": "For example, ___."},
        {"label": "Explain", "instruction": "Explain how the evidence supports your answer.", "frame": "This shows that ___."},
    ])
    if not isinstance(task["structure"], list):
        raise ValueError("writing structure must be a list")
    task.setdefault("focus_words", context.get("focus_words", []))
    if not isinstance(task["focus_words"], list):
        raise ValueError("writing focus_words must be a list")
    task.setdefault("opinion", {})
    if not isinstance(task["opinion"], dict):
        raise ValueError("writing opinion must be an object")
    examples = task.setdefault("examples", [])
    if not isinstance(examples, list):
        raise ValueError("writing examples must be a list")
    for idx, item in enumerate(examples, 1):
        if not isinstance(item, dict):
            raise ValueError(f"writing example {idx} must be an object")
        item.setdefault("id", f"example_{idx:03d}")
        item.setdefault("reference_sentence", item.get("memorize_line") or item.get("example", ""))
        item.setdefault("memorize_line", item.get("reference_sentence", ""))

    practice = task.setdefault("practice", {})
    if not isinstance(practice, dict):
        raise ValueError("writing practice must be an object")
    practice.setdefault("word_sentences", [])
    if not isinstance(practice["word_sentences"], list):
        raise ValueError("writing word_sentences must be a list")
    if not practice["word_sentences"]:
        practice["word_sentences"] = [
            {
                "word": item.get("word", ""),
                "prompt": f"Use {item.get('word', 'this word')} in one original sentence about today's topic.",
                "model": f"A clear sentence can use {item.get('word', 'this word')} to explain an idea.",
            }
            for item in task["focus_words"]
            if isinstance(item, dict) and item.get("word")
        ]
    practice.setdefault("draft_task", task["writing_prompt"])
    practice.setdefault(
        "revision_task",
        "Revise one sentence, add a specific detail, check your focus words, and confirm the three paragraphs.",
    )
    practice.setdefault("checklist", [
        "I answered the prompt directly.",
        "I included evidence or a specific detail.",
        "I explained how the evidence supports my answer.",
        "I used an introduction, body, and conclusion paragraph.",
        "I checked capitals, punctuation, and complete sentences.",
    ])
    if not isinstance(practice["checklist"], list):
        raise ValueError("writing checklist must be a list")
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
