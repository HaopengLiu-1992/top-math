import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from domain.daily_task import ENGLISH_READING, ENGLISH_VOCABULARY, ENGLISH_WRITING, MATH_HOMEWORK
from storage import daily_task_store, mark_buffer, reading_store, vocabulary_store, writing_store
from services import feedback_service, vocabulary_service, writing_service
from prompts import vocabulary_prompt


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

    def test_feedback_service_scores_scoped_marks(self):
        mark_buffer.clear_for(ENGLISH_READING, "2099-01-01")
        mark_buffer.init_for(ENGLISH_READING, "2099-01-01", {"q1": None, "q2": None})

        feedback_service.mark_item_for(ENGLISH_READING, "2099-01-01", "q1", True)
        feedback_service.mark_item_for(ENGLISH_READING, "2099-01-01", "q2", False)

        self.assertEqual(
            feedback_service.calc_score_for(ENGLISH_READING, "2099-01-01"),
            (1, 2),
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
                    "correct": None,
                    "known": None,
                    "last_seen": "2099-01-01",
                    "times_seen": 1,
                    "times_wrong": 0,
                    "category": "math_operations",
                    "is_review": False,
                }
            },
        )

    def test_vocabulary_word_bank_has_large_candidate_pool(self):
        self.assertGreaterEqual(len(vocabulary_store.load_word_bank()), 10000)

    def test_vocabulary_index_groups_large_bank_before_prompting(self):
        index = vocabulary_store.load_word_index()

        self.assertIn("cn_middle_school", index["by_stage_category"])
        self.assertIn("math_operations", index["by_stage_category"]["cn_middle_school"])
        self.assertGreaterEqual(
            sum(
                len(words)
                for stage in index["by_stage_category"].values()
                for words in stage.values()
            ),
            10000,
        )

    def test_vocabulary_selection_starts_from_basic_stage(self):
        with patch("services.vocabulary_service._seen_words", return_value=set()):
            new_words, review_words = vocabulary_service._select_words("2099-01-01")

        self.assertEqual(len(new_words), 20)
        self.assertEqual(review_words, [])
        self.assertTrue(all(w["cn_stage"] == "cn_middle_school" for w in new_words))
        self.assertTrue(all(w["source"] == "curated_math_science_core" for w in new_words))
        self.assertIn("sum", {w["word"] for w in new_words})

    def test_vocabulary_selection_avoids_unvetted_dictionary_words(self):
        bank = vocabulary_store.load_word_bank()
        curated = [
            item["word"]
            for item in bank
            if item.get("source") == "curated_math_science_core"
        ]

        with patch("services.vocabulary_service._seen_words", return_value=set(curated[:60])):
            new_words, review_words = vocabulary_service._select_words("2099-01-02")

        selected = {item["word"] for item in new_words}
        self.assertEqual(len(new_words), 15)
        self.assertEqual(len(review_words), 5)
        self.assertNotIn("aaronic", selected)
        self.assertTrue(all(item["source"] == "curated_math_science_core" for item in new_words))

    def test_vocabulary_prompt_only_contains_selected_words(self):
        with patch("services.vocabulary_service._seen_words", return_value=set()):
            new_words, review_words = vocabulary_service._select_words("2099-01-01")
        prompt = vocabulary_prompt.user_prompt("2099-01-01", 6, new_words, review_words)

        self.assertIn('"word": "sum"', prompt)
        self.assertLess(len(prompt), 20000)
        self.assertNotIn("academic_word_bank_10000", prompt)

    def test_vocabulary_regeneration_ignores_current_date_seen_words(self):
        original_root = daily_task_store.TASK_ROOT
        with tempfile.TemporaryDirectory() as tmp:
            try:
                daily_task_store.TASK_ROOT = Path(tmp)
                vocabulary_store.save_task("2099-01-01", {"date": "2099-01-01"})
                vocabulary_store.save_meta("2099-01-01", {
                    "sum": {
                        "known": None,
                        "last_seen": "2099-01-01",
                        "times_seen": 1,
                        "times_wrong": 0,
                        "category": "math_operations",
                        "is_review": False,
                    }
                })

                self.assertNotIn("sum", vocabulary_service._seen_words(exclude_date="2099-01-01"))
                self.assertIn("sum", vocabulary_service._seen_words(exclude_date="2099-01-02"))
            finally:
                daily_task_store.TASK_ROOT = original_root

    def test_reading_meta_uses_question_ids(self):
        task = {
            "questions": [
                {"id": "q_001", "type": "main_idea", "skill": "main idea"}
            ]
        }

        self.assertEqual(
            reading_store.build_meta(task),
            {
                "q_001": {
                    "correct": None,
                    "skill": "main idea",
                    "question_type": "main_idea",
                }
            },
        )

    def test_writing_meta_tracks_opinion_and_examples(self):
        task = {
            "opinion": {"claim": "Practice helps students improve."},
            "examples": [
                {"id": "example_001", "memorize_line": "For example, daily reading builds vocabulary."},
                {"id": "example_002", "memorize_line": "Also, science notes help students explain evidence."},
                {"id": "example_003", "memorize_line": "Finally, math practice makes problem solving faster."},
            ],
        }

        meta = writing_store.build_meta(task)

        self.assertEqual(set(meta), {"opinion", "example_001", "example_002", "example_003"})
        self.assertTrue(all(item["correct"] is None for item in meta.values()))
        self.assertTrue(all(item["skill"] == "writing_memorization" for item in meta.values()))

    def test_writing_task_normalization_builds_recitation_checks(self):
        task = {
            "opinion": {"claim": "Practice helps.", "memorize_line": "I believe practice helps."},
            "examples": [
                {"memorize_line": "For example, reading builds vocabulary."},
                {"memorize_line": "Also, science notes explain evidence."},
                {"memorize_line": "Finally, math practice improves speed."},
            ],
        }

        writing_service._normalize_task(task)

        self.assertEqual([item["id"] for item in task["examples"]],
                         ["example_001", "example_002", "example_003"])
        self.assertEqual(
            [item["id"] for item in task["practice"]["recitation_check"]],
            ["opinion", "example_001", "example_002", "example_003"],
        )

    def test_store_lists_multiple_scopes(self):
        original_root = daily_task_store.TASK_ROOT
        with tempfile.TemporaryDirectory() as tmp:
            try:
                daily_task_store.TASK_ROOT = Path(tmp)
                daily_task_store.save_task(MATH_HOMEWORK, "2099-01-01", {"date": "2099-01-01"})
                daily_task_store.save_task(ENGLISH_READING, "2099-01-01", {"date": "2099-01-01"})
                daily_task_store.save_task(ENGLISH_WRITING, "2099-01-01", {"date": "2099-01-01"})

                records = daily_task_store.list_task_records([MATH_HOMEWORK, ENGLISH_READING, ENGLISH_WRITING])
                self.assertEqual(len(records), 3)
                self.assertEqual({r["scope"] for r in records}, {MATH_HOMEWORK, ENGLISH_READING, ENGLISH_WRITING})
            finally:
                daily_task_store.TASK_ROOT = original_root


if __name__ == "__main__":
    unittest.main()
