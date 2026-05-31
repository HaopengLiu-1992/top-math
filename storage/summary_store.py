import json
from pathlib import Path

SUMMARY_ROOT = Path("output/summaries")


def summary_dir(start_date: str, end_date: str) -> Path:
    return SUMMARY_ROOT / f"{start_date}_to_{end_date}"


def analysis_path(start_date: str, end_date: str) -> Path:
    return summary_dir(start_date, end_date) / "analysis.json"


def feedback_report_path(start_date: str, end_date: str) -> Path:
    return summary_dir(start_date, end_date) / "feedback_report.json"


def load_analysis(start_date: str, end_date: str) -> dict | None:
    return _load_json(analysis_path(start_date, end_date))


def save_analysis(analysis: dict, start_date: str, end_date: str):
    _save_json(analysis, analysis_path(start_date, end_date))


def load_feedback_report(start_date: str, end_date: str) -> dict | None:
    return _load_json(feedback_report_path(start_date, end_date))


def save_feedback_report(report: dict, start_date: str, end_date: str):
    _save_json(report, feedback_report_path(start_date, end_date))


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _save_json(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
