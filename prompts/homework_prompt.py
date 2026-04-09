import json
from pathlib import Path

_INSTRUCTION = Path("config/instruction.md")


def system_prompt() -> str:
    return _INSTRUCTION.read_text()


def user_prompt(day: int, date_str: str, recent_topics: list[str], forbidden: set) -> str:
    import re
    _MD5_RE = re.compile(r'^[0-9a-f]{32}$')
    # Only pass raw fingerprint strings — MD5 hashes are unreadable to the model
    raw_fps = sorted(f for f in forbidden if not _MD5_RE.match(f))

    return f"""Generate homework for:
Day: {day}
Date: {date_str}

Recently covered topics (past 14 days) — avoid repeating unless it is a review day:
{json.dumps(recent_topics, indent=2)}

Forbidden fingerprints — do NOT generate any question whose fingerprint matches these exactly:
{json.dumps(raw_fps, indent=2)}

Output ONLY valid JSON. No markdown, no explanation."""
