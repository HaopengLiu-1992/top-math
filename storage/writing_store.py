import json
from pathlib import Path

from domain.daily_task import ENGLISH_WRITING
from storage import daily_task_store


def load_task(date_str: str) -> dict | None:
    return daily_task_store.load_task(ENGLISH_WRITING, date_str)


def save_task(date_str: str, task: dict):
    daily_task_store.save_task(ENGLISH_WRITING, date_str, task)


def load_meta(date_str: str) -> dict:
    return daily_task_store.load_meta(ENGLISH_WRITING, date_str)


def save_meta(date_str: str, meta: dict):
    daily_task_store.save_meta(ENGLISH_WRITING, date_str, meta)


def pdf_dir(date_str: str) -> Path:
    return daily_task_store.pdf_day_dir(ENGLISH_WRITING, date_str)


def list_dates() -> list[str]:
    return daily_task_store.list_dates(ENGLISH_WRITING)


def delete_for_date(date_str: str):
    daily_task_store.delete_for_date(ENGLISH_WRITING, date_str)
    delete_submission(date_str)


def submission_path(date_str: str) -> Path:
    return daily_task_store.raw_day_dir(ENGLISH_WRITING, date_str) / "submission.json"


def load_submission(date_str: str) -> dict:
    path = submission_path(date_str)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_submission(date_str: str, submission: dict):
    path = submission_path(date_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(submission, indent=2, ensure_ascii=False))


def delete_submission(date_str: str):
    path = submission_path(date_str)
    if path.exists():
        path.unlink()


def build_meta(task: dict) -> dict:
    if task.get("task_version") == 2:
        return {
            "draft": {
                "correct": None,
                "skill": "writing_structure_evidence",
                "label": "First draft and content revision",
            },
            "revision": {
                "correct": None,
                "skill": "writing_language_revision",
                "label": "Language-focused revision",
            },
        }

    focus_words = task.get("focus_words") or []
    if focus_words:
        items = [
            {
                "id": f"word_{item.get('word', idx)}",
                "label": f"Use {item.get('word', f'word {idx}')}",
                "skill": "writing_vocabulary",
            }
            for idx, item in enumerate(focus_words, 1)
            if isinstance(item, dict)
        ]
        items.extend([
            {"id": "draft", "label": "First draft", "skill": "writing_draft"},
            {"id": "revision", "label": "Revised draft", "skill": "writing_revision"},
        ])
        return {
            item["id"]: {
                "correct": None,
                "skill": item["skill"],
                "label": item["label"],
            }
            for item in items
        }

    opinion = task.get("opinion", {})
    examples = task.get("examples", [])
    items = [{"id": "opinion", "label": opinion.get("claim", "Opinion")}]
    items.extend({
        "id": item.get("id", f"example_{idx:03d}"),
        "label": item.get("memorize_line") or item.get("example") or f"Example {idx}",
    } for idx, item in enumerate(examples, 1))
    return {
        item["id"]: {
            "correct": None,
            "skill": "writing_memorization",
            "label": item["label"],
        }
        for item in items
    }
