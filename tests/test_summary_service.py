import tempfile
import unittest
from pathlib import Path

from prompts import analysis_prompt, feedback_report_prompt
from services import summary_service
from storage import summary_store


class SummaryServiceTests(unittest.TestCase):
    def test_default_range_is_inclusive_week(self):
        start_date, end_date = summary_service.default_range("2026-05-31")

        self.assertEqual(start_date, "2026-05-25")
        self.assertEqual(end_date, "2026-05-31")

    def test_summary_store_round_trip_by_range(self):
        original_root = summary_store.SUMMARY_ROOT
        with tempfile.TemporaryDirectory() as tmp:
            try:
                summary_store.SUMMARY_ROOT = Path(tmp)
                analysis = {"week_summary": "Good progress"}
                report = {"headline": "A steady week"}

                summary_store.save_analysis(analysis, "2026-05-25", "2026-05-31")
                summary_store.save_feedback_report(report, "2026-05-25", "2026-05-31")

                self.assertEqual(
                    summary_store.load_analysis("2026-05-25", "2026-05-31"),
                    analysis,
                )
                self.assertEqual(
                    summary_store.load_feedback_report("2026-05-25", "2026-05-31"),
                    report,
                )
            finally:
                summary_store.SUMMARY_ROOT = original_root

    def test_summary_prompts_include_explicit_range(self):
        logs = [{"date": "2026-05-30", "auto_score_pct": 80.0}]
        incorrect = [{"id": "p1", "question": "2+2", "answer": "4"}]

        analysis = analysis_prompt.user_prompt("2026-05-25", "2026-05-31", logs, incorrect)
        report = feedback_report_prompt.user_prompt("2026-05-25", "2026-05-31", logs, incorrect)

        self.assertIn("2026-05-25 through 2026-05-31", analysis)
        self.assertIn("2026-05-25 through 2026-05-31", report)
        self.assertIn("Task logs", report)


if __name__ == "__main__":
    unittest.main()
