import json
from pathlib import Path

_INSTRUCTION = Path("config/feedback_report_instruction.md")


def system_prompt() -> str:
    return _INSTRUCTION.read_text()


def user_prompt(start_date: str, end_date_or_logs, logs_or_incorrect=None,
                incorrect_questions: list[dict] | None = None) -> str:
    if incorrect_questions is None:
        end_date = start_date
        weekly_logs = end_date_or_logs
        incorrect_questions = logs_or_incorrect
    else:
        end_date = end_date_or_logs
        weekly_logs = logs_or_incorrect

    return f"""Generate a parent-facing feedback summary for {start_date} through {end_date}.

Task logs:
{json.dumps(weekly_logs, indent=2)}

Incorrect questions in this range (full detail):
{json.dumps(incorrect_questions, indent=2)}

Output ONLY valid JSON. No markdown, no explanation."""
