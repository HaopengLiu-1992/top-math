import json
from pathlib import Path

_INSTRUCTION = Path("config/instruction.md")


def system_prompt() -> str:
    return _INSTRUCTION.read_text()


def user_prompt(day: int, date_str: str, recent_topics: list[str], forbidden_hashes: set) -> str:
    forbidden_list = list(forbidden_hashes)[:100]

    return f"""Generate homework for:
Day: {day}
Date: {date_str}

Recently covered topics (past 14 days) — avoid repeating unless it is a review day:
{json.dumps(recent_topics, indent=2)}

Forbidden fingerprint hashes (do not generate questions matching these):
{json.dumps(forbidden_list, indent=2)}

Output ONLY valid JSON. No markdown, no explanation."""
