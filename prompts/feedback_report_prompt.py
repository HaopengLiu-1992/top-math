import json
from pathlib import Path

_INSTRUCTION = Path("config/feedback_report_instruction.md")


def system_prompt() -> str:
    return _INSTRUCTION.read_text()


def user_prompt(date_str: str, weekly_logs: list[dict], incorrect_questions: list[dict]) -> str:
    return f"""Generate the weekly feedback report for the week ending {date_str}.

Weekly homework logs:
{json.dumps(weekly_logs, indent=2)}

Incorrect questions this week (full detail):
{json.dumps(incorrect_questions, indent=2)}

Output ONLY valid JSON. No markdown, no explanation."""
