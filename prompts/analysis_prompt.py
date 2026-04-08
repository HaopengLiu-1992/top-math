import json
from pathlib import Path

_INSTRUCTION = Path("config/analysis_instruction.md")


def system_prompt() -> str:
    return _INSTRUCTION.read_text()


def user_prompt(date_str: str, weekly_logs: list[dict], incorrect_questions: list[dict]) -> str:
    return f"""Analyze Jessie's math performance for the week ending {date_str}.

Weekly homework logs (scores, topics, incorrect question IDs):
{json.dumps(weekly_logs, indent=2)}

Full incorrect questions from this week:
{json.dumps(incorrect_questions, indent=2)}

Output ONLY valid JSON. No markdown, no explanation."""
