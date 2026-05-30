import json
from pathlib import Path

LESSON_ROOT = Path("output/lessons")


def lesson_path(subject: str, grade_level: int, topic_id: str,
                lesson_type: str = "intro") -> Path:
    return (LESSON_ROOT / _safe(subject) / f"grade{grade_level}" /
            _safe(topic_id) / f"{_safe(lesson_type)}_v1.json")


def load_lesson(subject: str, grade_level: int, topic_id: str,
                lesson_type: str = "intro") -> dict | None:
    p = lesson_path(subject, grade_level, topic_id, lesson_type)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def save_lesson(lesson: dict, subject: str, grade_level: int, topic_id: str,
                lesson_type: str = "intro") -> Path:
    p = lesson_path(subject, grade_level, topic_id, lesson_type)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(lesson, indent=2, ensure_ascii=False))
    return p


def _safe(value: str) -> str:
    return value.strip().replace("/", "_").replace("\\", "_").replace(" ", "_")
