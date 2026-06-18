import json
from pathlib import Path

from domain.daily_task import TaskScope

TASK_ROOT = Path("output/tasks")


def raw_day_dir(scope: TaskScope, date_str: str) -> Path:
    y, m, d = date_str.split("-")
    return TASK_ROOT / scope.subject / scope.task_type / "raw" / y / m / d


def pdf_day_dir(scope: TaskScope, date_str: str) -> Path:
    y, m, d = date_str.split("-")
    return TASK_ROOT / scope.subject / scope.task_type / "pdf" / y / m / d


def task_path(scope: TaskScope, date_str: str) -> Path:
    return raw_day_dir(scope, date_str) / "task.json"


def meta_path(scope: TaskScope, date_str: str) -> Path:
    return raw_day_dir(scope, date_str) / "meta.json"


def fingerprints_path(scope: TaskScope, date_str: str) -> Path:
    return raw_day_dir(scope, date_str) / "fingerprints.json"


def load_task(scope: TaskScope, date_str: str) -> dict | None:
    p = task_path(scope, date_str)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def save_task(scope: TaskScope, date_str: str, task: dict):
    p = task_path(scope, date_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(task, indent=2, ensure_ascii=False))


def load_meta(scope: TaskScope, date_str: str) -> dict:
    p = meta_path(scope, date_str)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def save_meta(scope: TaskScope, date_str: str, meta: dict):
    p = meta_path(scope, date_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(meta, indent=2, ensure_ascii=False))


def load_fingerprints(scope: TaskScope, date_str: str) -> list[str]:
    p = fingerprints_path(scope, date_str)
    if not p.exists():
        return []
    return json.loads(p.read_text())


def save_fingerprints(scope: TaskScope, date_str: str, hashes: list[str]):
    p = fingerprints_path(scope, date_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(hashes, indent=2))


def delete_fingerprints(scope: TaskScope, date_str: str):
    p = fingerprints_path(scope, date_str)
    if p.exists():
        p.unlink()


def list_dates(scope: TaskScope) -> list[str]:
    dates = []
    root = TASK_ROOT / scope.subject / scope.task_type / "raw"
    for p in root.glob("*/*/*/task.json"):
        parts = p.parts
        dates.append(f"{parts[-4]}-{parts[-3]}-{parts[-2]}")
    return sorted(dates)


def list_task_records(scopes: list[TaskScope]) -> list[dict]:
    records = []
    for scope in scopes:
        for date_str in list_dates(scope):
            task = load_task(scope, date_str)
            if task:
                records.append({
                    "scope": scope,
                    "date": date_str,
                    "subject": scope.subject,
                    "task_type": scope.task_type,
                    "task": task,
                })
    return sorted(records, key=lambda item: (item["date"], item["subject"], item["task_type"]))


def delete_for_date(scope: TaskScope, date_str: str):
    for p in [task_path(scope, date_str), meta_path(scope, date_str), fingerprints_path(scope, date_str)]:
        if p.exists():
            p.unlink()

    pdf_dir = pdf_day_dir(scope, date_str)
    for name in ["questions.pdf", "answers.pdf", "vocabulary.pdf", "reading.pdf"]:
        p = pdf_dir / name
        if p.exists():
            p.unlink()
