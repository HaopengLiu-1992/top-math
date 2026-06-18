import json
from pathlib import Path

from domain.daily_task import ENGLISH_VOCABULARY
from storage import daily_task_store

WORD_BANK = Path("config/vocabulary/academic_word_bank_10000.json")
WORD_INDEX = Path("config/vocabulary/vocabulary_index.json")


def load_word_bank() -> list[dict]:
    return json.loads(WORD_BANK.read_text())


def load_word_index() -> dict:
    return json.loads(WORD_INDEX.read_text())


def load_task(date_str: str) -> dict | None:
    return daily_task_store.load_task(ENGLISH_VOCABULARY, date_str)


def save_task(date_str: str, task: dict):
    daily_task_store.save_task(ENGLISH_VOCABULARY, date_str, task)


def load_meta(date_str: str) -> dict:
    return daily_task_store.load_meta(ENGLISH_VOCABULARY, date_str)


def save_meta(date_str: str, meta: dict):
    daily_task_store.save_meta(ENGLISH_VOCABULARY, date_str, meta)


def pdf_dir(date_str: str) -> Path:
    return daily_task_store.pdf_day_dir(ENGLISH_VOCABULARY, date_str)


def list_dates() -> list[str]:
    return daily_task_store.list_dates(ENGLISH_VOCABULARY)


def delete_for_date(date_str: str):
    daily_task_store.delete_for_date(ENGLISH_VOCABULARY, date_str)


def build_meta(task: dict) -> dict:
    meta = {}
    for item in task.get("words", []):
        word = item["word"]
        meta[word] = {
            "correct": None,
            "known": None,
            "last_seen": task["date"],
            "times_seen": 1,
            "times_wrong": 0,
            "category": item.get("category"),
            "is_review": item.get("is_review", False),
        }
    return meta
