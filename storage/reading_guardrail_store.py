import json
from pathlib import Path

MEMORY_PATH = Path("output/reading_guardrail/concepts.json")


def load_records() -> list[dict]:
    if not MEMORY_PATH.exists():
        return []
    return json.loads(MEMORY_PATH.read_text())


def save_records(records: list[dict]):
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False))


def append_record(record: dict):
    records = load_records()
    if any(existing.get("external_passage_id") == record.get("external_passage_id")
           for existing in records):
        return
    records.append(record)
    save_records(records)
