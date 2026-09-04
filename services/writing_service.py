import json
import re
from datetime import date, timedelta
from difflib import SequenceMatcher

from domain.daily_task import ENGLISH_READING
from providers.base import ModelProvider
from providers.default_provider import get_default_provider
from prompts import writing_prompt
from storage import reading_store, writing_store

MAX_GENERATION_RETRIES = 3
SIMILARITY_THRESHOLD = 0.86
WRITING_MODES = ("summary", "opinion", "text_based_response")
MODE_LABELS = {
    "summary": "Summary",
    "opinion": "Opinion / Argument",
    "text_based_response": "Text-Based Response",
}


class WritingGenerationError(RuntimeError):
    """The provider could not produce a valid writing task."""


class WritingReviewError(RuntimeError):
    """The provider could not produce focused feedback for the student's draft."""


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

    context = _writing_context(today)
    history_context = _history_context(_recent_history(today))
    accepted_task = None
    last_error = "unknown writing generation error"
    for attempt in range(MAX_GENERATION_RETRIES):
        raw = provider.complete(
            system=writing_prompt.system_prompt(),
            user=writing_prompt.user_prompt(
                today,
                grade_level,
                focus,
                history=history_context,
                feedback=last_error if attempt else "",
                writing_mode=context["writing_mode"],
                source_context=context["source"],
            ),
            max_tokens=5000,
        )
        try:
            candidate = _parse_json_response(raw)
            _normalize_task(candidate, context=context)
            errors = _validate_task(candidate, history_context, context["writing_mode"])
            if errors:
                raise ValueError("; ".join(errors))
            accepted_task = candidate
            break
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)

    if accepted_task is None:
        raise WritingGenerationError(
            f"Writing generation did not pass validation: {last_error}"
        )

    task = accepted_task
    task["date"] = today
    task["subject"] = "english"
    task["task_type"] = "writing"
    task["task_version"] = 2
    task["grade_level"] = grade_level
    task["focus"] = focus
    task["writing_mode"] = context["writing_mode"]
    task["mode_label"] = MODE_LABELS[context["writing_mode"]]
    task["target_words"] = writing_prompt.TARGET_WORDS
    task["target_range"] = [writing_prompt.MIN_WORDS, writing_prompt.MAX_WORDS]
    task["model"] = provider.name
    task["writing_guardrail"] = {
        "history_days": 30,
        "writing_mode": context["writing_mode"],
        "target_words": writing_prompt.TARGET_WORDS,
        "vocabulary_is_separate": True,
        "source_task": "history_english_reading" if context["source"].get("text") else None,
    }

    writing_store.save_task(today, task)
    writing_store.save_meta(today, writing_store.build_meta(task))
    if force:
        writing_store.delete_submission(today)
    _ensure_pdfs(task)
    return task


def review_draft(task: dict, draft: str, review_round: int,
                 provider: ModelProvider | None = None) -> dict:
    provider = provider or get_default_provider()
    draft = draft.strip()
    if review_round not in {1, 2}:
        raise ValueError("review_round must be 1 or 2")
    if len(draft.split()) < 10:
        raise WritingReviewError("Write at least 10 words before requesting feedback.")

    raw = provider.complete(
        system=writing_prompt.review_system_prompt(),
        user=writing_prompt.review_user_prompt(task, draft, review_round),
        max_tokens=1800,
    )
    try:
        feedback = _parse_json_response(raw)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise WritingReviewError(f"Writing feedback was not valid JSON: {exc}") from exc

    errors = _validate_review(feedback, review_round)
    if errors:
        raise WritingReviewError("; ".join(errors))

    submission = writing_store.load_submission(task["date"])
    key = f"round_{review_round}"
    submission[key] = {
        "draft": draft,
        "feedback": feedback,
        "model": provider.name,
    }
    writing_store.save_submission(task["date"], submission)
    return feedback


def _writing_context(date_str: str) -> dict:
    """Use reading as source material while keeping vocabulary practice separate."""
    reading_task = reading_store.load_task(ENGLISH_READING, date_str) or {}
    passage = reading_task.get("passage") or {}
    source = {
        "title": passage.get("title", ""),
        "text": passage.get("text", ""),
    }
    day_number = date.fromisoformat(date_str).toordinal()
    return {
        "writing_mode": WRITING_MODES[day_number % len(WRITING_MODES)],
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
        practice = task.get("practice") or {}
        records.append({
            "date": history_date,
            "prompt": task.get("writing_prompt", ""),
            "sample": practice.get("sample_response", ""),
        })
    return records


def _history_context(records: list[dict]) -> dict:
    return {
        "avoid_prompts": _unique([item.get("prompt", "") for item in records])[:10],
        "avoid_samples": _unique([item.get("sample", "") for item in records])[:6],
    }


def _validate_task(task: dict, history: dict, writing_mode: str) -> list[str]:
    errors: list[str] = []
    if task.get("writing_mode") != writing_mode:
        errors.append(f"writing mode must be {writing_mode}")
    if not task.get("writing_prompt"):
        errors.append("missing writing prompt")

    source = task.get("source") or {}
    if not isinstance(source, dict):
        return ["source must be an object"]
    if writing_mode in {"summary", "text_based_response"} and not source.get("text"):
        errors.append("reading-based writing needs a source passage")
    if writing_mode == "opinion" and source.get("text"):
        errors.append("opinion mode must not include a source passage")

    structure = task.get("structure")
    if not isinstance(structure, list) or len(structure) != 3:
        errors.append("expected exactly three Answer/Evidence/Explain structure steps")

    practice = task.get("practice") or {}
    if not isinstance(practice, dict):
        return errors + ["practice must be an object"]
    rounds = practice.get("revision_rounds") or []
    if [item.get("round") for item in rounds if isinstance(item, dict)] != [1, 2]:
        errors.append("expected two ordered revision rounds")
    sample = practice.get("sample_response", "")
    sample_words = len(sample.split())
    if not writing_prompt.MIN_WORDS <= sample_words <= writing_prompt.MAX_WORDS:
        errors.append(
            f"sample response must be {writing_prompt.MIN_WORDS}-{writing_prompt.MAX_WORDS} words"
        )

    recent_prompts = history.get("avoid_prompts", [])
    if any(_similarity(task.get("writing_prompt", ""), previous) >= SIMILARITY_THRESHOLD
           for previous in recent_prompts):
        errors.append("writing prompt is too similar to recent writing")
    return errors


def _validate_review(feedback: dict, review_round: int) -> list[str]:
    errors = []
    if feedback.get("round") != review_round:
        errors.append(f"feedback round must be {review_round}")
    required = {"strength", "next_step"}
    if review_round == 1:
        required.update({"answer_feedback", "evidence_feedback"})
        forbidden = {"corrections", "language_category"}
        if forbidden.intersection(feedback):
            errors.append("round 1 must not include language corrections")
    else:
        required.add("language_category")
        corrections = feedback.get("corrections")
        if not isinstance(corrections, list) or len(corrections) > 2:
            errors.append("round 2 must include at most two corrections")
        elif any(not isinstance(item, dict) or
                 not all(item.get(field) for field in ("original", "revision", "why"))
                 for item in corrections):
            errors.append("each language correction needs original, revision, and why")
    for field in required:
        if not feedback.get(field):
            errors.append(f"missing review field: {field}")
    return errors


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", value.lower()).strip()


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
    context = context or {}
    mode = context.get("writing_mode", task.get("writing_mode", "opinion"))
    task.setdefault("task_version", 2)
    task.setdefault("title", f"Daily 50-Word Writing — {MODE_LABELS.get(mode, 'Writing')}")
    task.setdefault("estimated_minutes", 20)
    task.setdefault("writing_mode", mode)
    task.setdefault("mode_label", MODE_LABELS.get(mode, "Opinion / Argument"))
    task["target_words"] = writing_prompt.TARGET_WORDS
    task["target_range"] = [writing_prompt.MIN_WORDS, writing_prompt.MAX_WORDS]
    task.setdefault("time_plan", [
        {"minutes": 3, "activity": "Plan Answer/Claim, Evidence, and Explain."},
        {"minutes": 10, "activity": "Write one paragraph of about 50 words."},
        {"minutes": 7, "activity": "Revise ideas, then one language skill."},
    ])

    supplied_source = context.get("source") or {}
    if mode in {"summary", "text_based_response"} and supplied_source.get("text"):
        task["source"] = supplied_source
    else:
        task.setdefault("source", {"title": "", "text": ""})
    if mode == "opinion":
        task["source"] = {"title": "", "text": ""}

    task.setdefault("structure", [
        {"label": "Answer / Claim", "instruction": "Answer directly.", "frame": "I think ___ because ___."},
        {"label": "Evidence", "instruction": "Add one or two details.", "frame": "One detail is ___."},
        {"label": "Explain", "instruction": "Connect the evidence.", "frame": "This shows that ___."},
    ])
    practice = task.setdefault("practice", {})
    if not isinstance(practice, dict):
        raise ValueError("writing practice must be an object")
    practice.setdefault("draft_task", "Write one 45-65 word paragraph, normally 5-7 sentences.")
    practice.setdefault("revision_rounds", [
        {"round": 1, "focus": "structure_and_evidence",
         "instruction": "Check only the answer/claim, evidence, and explanation."},
        {"round": 2, "focus": "one_language_skill",
         "instruction": "Correct only one recurring language category."},
    ])
    practice.setdefault("checklist", [
        "I answered the prompt directly.",
        "I included accurate evidence or a specific detail.",
        "I explained how the evidence supports my answer.",
        "I wrote one paragraph of about 50 words.",
        "I checked capitals, punctuation, and complete sentences.",
    ])
