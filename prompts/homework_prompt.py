import json
from pathlib import Path

_INSTRUCTION = Path("config/instruction.md")


def system_prompt() -> str:
    return _INSTRUCTION.read_text()


def user_prompt(day: int, date_str: str, recent_topics: list[str], forbidden: set,
                include_forbidden: bool = False) -> str:
    import re
    _MD5_RE = re.compile(r'^[0-9a-f]{32}$')

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

Recently covered topics (past 14 days) — avoid repeating unless it is a review day:
{json.dumps(recent_topics, indent=2)}
{forbidden_section}
Output ONLY valid JSON. No markdown, no explanation."""
