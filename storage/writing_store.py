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


def build_meta(task: dict) -> dict:
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
