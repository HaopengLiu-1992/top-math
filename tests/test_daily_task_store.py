import tempfile
import unittest
from pathlib import Path

from domain.daily_task import ENGLISH_VOCABULARY, MATH_HOMEWORK
from storage import daily_task_store, mark_buffer, vocabulary_store


class DailyTaskStoreTests(unittest.TestCase):
    def test_store_round_trip_uses_scope(self):
        original_root = daily_task_store.TASK_ROOT
        with tempfile.TemporaryDirectory() as tmp:
            try:
                daily_task_store.TASK_ROOT = Path(tmp)
                task = {"date": "2099-01-01", "subject": "math"}
                daily_task_store.save_task(MATH_HOMEWORK, "2099-01-01", task)

                self.assertEqual(
                    daily_task_store.load_task(MATH_HOMEWORK, "2099-01-01"),
                    task,
                )
                self.assertIsNone(
                    daily_task_store.load_task(ENGLISH_VOCABULARY, "2099-01-01")
                )
                self.assertEqual(daily_task_store.list_dates(MATH_HOMEWORK), ["2099-01-01"])
            finally:
                daily_task_store.TASK_ROOT = original_root

    def test_mark_buffer_keeps_scopes_separate(self):
        mark_buffer.clear_for(MATH_HOMEWORK, "2099-01-01")
        mark_buffer.clear_for(ENGLISH_VOCABULARY, "2099-01-01")

        mark_buffer.init_for(MATH_HOMEWORK, "2099-01-01", {"q1": None})
        mark_buffer.init_for(ENGLISH_VOCABULARY, "2099-01-01", {"word1": None})
        mark_buffer.set_mark_for(MATH_HOMEWORK, "2099-01-01", "q1", True)
        mark_buffer.set_mark_for(ENGLISH_VOCABULARY, "2099-01-01", "word1", False)

        self.assertEqual(mark_buffer.get_marks_for(MATH_HOMEWORK, "2099-01-01"), {"q1": True})
        self.assertEqual(
            mark_buffer.get_marks_for(ENGLISH_VOCABULARY, "2099-01-01"),
            {"word1": False},
        )

    def test_vocabulary_meta_uses_words(self):
        task = {
            "date": "2099-01-01",
            "words": [
                {"word": "quotient", "category": "math_operations", "is_review": False}
            ],
        }

        self.assertEqual(
            vocabulary_store.build_meta(task),
            {
                "quotient": {
                    "known": None,
                    "last_seen": "2099-01-01",
                    "times_seen": 1,
                    "times_wrong": 0,
                    "category": "math_operations",
                    "is_review": False,
                }
            },
        )


if __name__ == "__main__":
    unittest.main()
