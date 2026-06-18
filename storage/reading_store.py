from pathlib import Path

from domain.daily_task import ENGLISH_READING, SCIENCE_READING, TaskScope
from storage import daily_task_store


def scope_for(subject: str) -> TaskScope:
    if subject == "science":
        return SCIENCE_READING
    return ENGLISH_READING


def load_task(scope: TaskScope, date_str: str) -> dict | None:
    return daily_task_store.load_task(scope, date_str)


def save_task(scope: TaskScope, date_str: str, task: dict):
    daily_task_store.save_task(scope, date_str, task)


def load_meta(scope: TaskScope, date_str: str) -> dict:
    return daily_task_store.load_meta(scope, date_str)


def save_meta(scope: TaskScope, date_str: str, meta: dict):
    daily_task_store.save_meta(scope, date_str, meta)


def pdf_dir(scope: TaskScope, date_str: str) -> Path:
    return daily_task_store.pdf_day_dir(scope, date_str)


def list_dates(scope: TaskScope) -> list[str]:
    return daily_task_store.list_dates(scope)


def delete_for_date(scope: TaskScope, date_str: str):
    daily_task_store.delete_for_date(scope, date_str)


def build_meta(task: dict) -> dict:
    meta = {}
    for item in task.get("questions", []):
        qid = item["id"]
        meta[qid] = {
            "correct": None,
            "skill": item.get("skill"),
            "question_type": item.get("type"),
        }
    return meta
