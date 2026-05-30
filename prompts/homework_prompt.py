import json
from pathlib import Path

from domain.curriculum import CurriculumTopic
from domain.learning_context import LearningContext

_INSTRUCTION = Path("config/instruction.md")


def system_prompt() -> str:
    return _INSTRUCTION.read_text()


def user_prompt(day: int, date_str: str, recent_topics: list[str], forbidden: set,
                include_forbidden: bool = False,
                context: LearningContext | None = None,
                topic: CurriculumTopic | None = None,
                cached_lesson: dict | None = None) -> str:
    import re
    _MD5_RE = re.compile(r'^[0-9a-f]{32}$')
    context = context or LearningContext(grade_level=5, include_lesson=False,
                                         include_hints=True,
                                         recent_topics=recent_topics)

    topic_section = topic.to_prompt_dict() if topic else None

    forbidden_section = ""
    if include_forbidden:
        raw_fps = sorted(f for f in forbidden if not _MD5_RE.match(f))
        if raw_fps:
            forbidden_section = f"""
Forbidden fingerprints — do NOT generate questions with these fingerprints:
{json.dumps(raw_fps, indent=2)}
"""

    return f"""Generate homework for:
Day: {day}
Date: {date_str}
Student: {context.student_id}
Subject: {context.subject}
Grade level: {context.grade_level}
Mode: {context.mode}
Difficulty policy: {context.difficulty_policy}
Include lesson: {context.include_lesson}
Include hints: {context.include_hints}

Target topic:
{json.dumps(topic_section, indent=2)}

Cached lesson, if any. Reuse it when present:
{json.dumps(cached_lesson, indent=2)}

Recently covered topics (past 14 days) — avoid repeating unless it is a review day:
{json.dumps(recent_topics, indent=2)}
{forbidden_section}
Output ONLY valid JSON. No markdown, no explanation."""
