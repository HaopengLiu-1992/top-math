import json
from pathlib import Path

_INSTRUCTION = Path("config/review_instruction.md")


def system_prompt() -> str:
    return _INSTRUCTION.read_text()


def user_prompt(date_str: str, incorrect_questions: list[dict]) -> str:
    return f"""Generate a Sunday Review session for:
Date: {date_str}

These are the questions Jessie answered incorrectly in the past 7 days:
{json.dumps(incorrect_questions, indent=2)}

Output ONLY valid JSON. No markdown, no explanation."""
