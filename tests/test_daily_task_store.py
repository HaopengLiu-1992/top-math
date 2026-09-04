import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from domain.daily_task import (
    ENGLISH_READING,
    ENGLISH_VOCABULARY,
    ENGLISH_WRITING,
    MATH_HOMEWORK,
    SCIENCE_READING,
)
from storage import daily_task_store, mark_buffer, reading_store, vocabulary_store, writing_store
from services import feedback_service, math_guardrail, vocabulary_service, writing_service
from prompts import vocabulary_prompt
from prompts import reading_prompt
from services import reading_guardrail
from storage import reading_guardrail_store


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
        bank = vocabulary_store.load_word_bank()
        self.assertGreaterEqual(len(bank), 10000)
        self.assertEqual(len({item["word"] for item in bank}), len(bank))
        self.assertTrue(all(item.get("definition") for item in bank))
        self.assertTrue(all(item.get("grade_min") <= item.get("grade_max") for item in bank))

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

    def test_vocabulary_selection_starts_from_curated_academic_layer(self):
        with patch("services.vocabulary_service._seen_words", return_value=set()):
            new_words, review_words = vocabulary_service._select_words("2099-01-01")

        self.assertEqual(len(new_words), 8)
        self.assertEqual(review_words, [])
        self.assertTrue(all(w["source"] == "curated_academic_core" for w in new_words))
        self.assertEqual({w["topic_group"] for w in new_words}, {"reasoning_and_evidence"})
        self.assertIn("analyze", {w["word"] for w in new_words})

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
        self.assertEqual(len(new_words), 8)
        self.assertEqual(len(review_words), 2)
        self.assertNotIn("aaronic", selected)
        self.assertTrue(all(item["source"] == "curated_academic_core" for item in new_words))

    def test_vocabulary_review_selection_rotates_away_from_bank_prefix(self):
        words = ["sum", "difference", "old_one", "old_two", "old_three", "old_four", "old_five"]
        bank = [{"word": word} for word in words]
        history = {
            "sum": {"last_seen": "2099-01-10", "times_seen": 5, "times_wrong": 0, "known": None},
            "difference": {"last_seen": "2099-01-10", "times_seen": 5, "times_wrong": 0, "known": None},
        }
        for index, word in enumerate(words[2:], 1):
            history[word] = {
                "last_seen": f"2099-01-0{index}",
                "times_seen": 1,
                "times_wrong": 0,
                "known": None,
            }

        selected = vocabulary_service._select_review_words(
            bank,
            set(history),
            history,
            "2099-01-11",
        )

        self.assertEqual(
            [item["word"] for item in selected],
            ["old_one", "old_two"],
        )

    def test_vocabulary_selection_never_falls_back_to_seen_words(self):
        bank = vocabulary_store.load_word_bank()
        seen = {
            item["word"] for item in bank
            if item.get("source") in vocabulary_service.TRUSTED_SOURCES
        }
        history = {
            word: {
                "last_seen": "2099-01-01",
                "times_seen": 1,
                "times_wrong": 0,
                "known": None,
            }
            for word in seen
        }

        with patch("services.vocabulary_service._seen_words", return_value=seen), \
             patch("services.vocabulary_service._word_history", return_value=history):
            new_words, review_words = vocabulary_service._select_words("2099-01-02")

        self.assertEqual(len(new_words), 8)
        self.assertEqual(len(review_words), 2)
        self.assertTrue(set(item["word"] for item in review_words).issubset(seen))
        self.assertTrue(set(item["word"] for item in new_words).isdisjoint(seen))

    def test_vocabulary_selection_respects_grade_band(self):
        bank = vocabulary_store.load_word_bank()
        index = vocabulary_store.load_word_index()
        by_word = {item["word"]: item for item in bank}
        curated_words = {
            item["word"]
            for item in bank
            if item.get("source") == "curated_math_science_core"
        }

        grade_five = vocabulary_service._select_new_words(
            index, by_word, curated_words, 50, grade_level=5
        )
        grade_eight = vocabulary_service._select_new_words(
            index, by_word, curated_words, 50, grade_level=8
        )

        self.assertTrue(all(item["grade_min"] <= 5 <= item["grade_max"] for item in grade_five))
        self.assertTrue(any(item["grade_min"] > 5 for item in grade_eight))

    def test_vocabulary_normalization_owns_word_membership_and_review_flags(self):
        new_words = [{"word": "alpha", "category": "math"}]
        review_words = [{"word": "beta", "category": "science"}]
        task = {
            "words": [
                {"word": "alpha", "is_review": True},
                {"word": "beta", "is_review": False},
            ]
        }

        normalized = vocabulary_service._normalize_generated_task(task, new_words, review_words)

        self.assertEqual([item["word"] for item in normalized["words"]], ["alpha", "beta"])
        self.assertFalse(normalized["words"][0]["is_review"])
        self.assertTrue(normalized["words"][1]["is_review"])
        with self.assertRaises(ValueError):
            vocabulary_service._normalize_generated_task(
                {"words": [{"word": "alpha"}, {"word": "beta"}, {"word": "extra"}]},
                new_words,
                review_words,
            )

    def test_vocabulary_generation_retries_invalid_word_membership(self):
        original_root = daily_task_store.TASK_ROOT

        class FakeVocabularyProvider:
            name = "Fake Vocabulary"

            def __init__(self):
                self.calls = 0

            def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
                self.calls += 1
                chosen = ["alpha", "invented"] if self.calls == 1 else ["beta", "alpha"]
                words = [{
                    "word": word,
                    "chinese": "测试",
                    "definition": f"definition of {word}",
                    "example": f"Use {word} in context.",
                    "quick_check": f"What does {word} mean?",
                    "answer": f"definition of {word}",
                } for word in chosen]
                return json.dumps({
                    "words": words,
                    "practice": {
                        "matching": [{"word": word, "definition": f"definition of {word}"}
                                     for word in chosen],
                        "fill_blank": [{"sentence": "Use ___.", "answer": word}
                                       for word in chosen],
                        "keyword_reading": [
                            {"question": f"Question {index}?", "keyword": "alpha", "meaning": "test"}
                            for index in range(3)
                        ],
                    },
                })

        try:
            with tempfile.TemporaryDirectory() as tmp:
                daily_task_store.TASK_ROOT = Path(tmp)
                provider = FakeVocabularyProvider()
                with patch(
                    "services.vocabulary_service._select_words",
                    return_value=(
                        [{"word": "beta", "category": "math"}],
                        [{"word": "alpha", "category": "science"}],
                    ),
                ), patch("services.vocabulary_service._ensure_pdfs"):
                    task = vocabulary_service.generate("2099-01-01", provider)

                self.assertEqual(provider.calls, 2)
                self.assertEqual([item["word"] for item in task["words"]], ["beta", "alpha"])
                self.assertFalse(task["words"][0]["is_review"])
                self.assertTrue(task["words"][1]["is_review"])
        finally:
            daily_task_store.TASK_ROOT = original_root

    def test_vocabulary_prompt_only_contains_selected_words(self):
        with patch("services.vocabulary_service._seen_words", return_value=set()):
            new_words, review_words = vocabulary_service._select_words("2099-01-01")
        prompt = vocabulary_prompt.user_prompt("2099-01-01", 6, new_words, review_words)

        self.assertIn('"word": "analyze"', prompt)
        self.assertIn("There are 8 new words", prompt)
        self.assertLess(len(prompt), 20000)
        self.assertNotIn("academic_word_bank_10000", prompt)

    def test_vocabulary_prompt_includes_personal_prompt(self):
        prompt = vocabulary_prompt.user_prompt(
            "2099-01-01", 6, [], [], personal_prompt="Use examples from science class"
        )

        self.assertIn("Personal prompt from the learner or parent", prompt)
        self.assertIn("Use examples from science class", prompt)

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

    def test_reading_guardrail_prompt_keeps_history_small(self):
        guardrail = {
            "slot": {
                "grade": 6,
                "domain": "informational",
                "topic": "technology",
                "subtopic": "how an invention changes daily life",
                "text_type": "expository",
                "skill": "main idea",
            },
            "core_concept": "how an invention changes daily life in a school setting",
            "avoid_concepts": ["old concept 1", "old concept 2"],
            "external_passage_id": "english-reading-2099-01-01-test",
        }

        prompt = reading_prompt.user_prompt(
            "2099-01-01",
            6,
            "english",
            "main idea",
            guardrail=guardrail,
        )

        self.assertIn("core_concept", prompt)
        self.assertIn("old concept 1", prompt)
        self.assertLess(len(prompt), 7000)

    def test_grade_six_english_reading_uses_ancient_history_curriculum(self):
        plan = reading_guardrail.prepare(
            ENGLISH_READING,
            "2099-01-01",
            6,
            "history and evidence",
        )

        self.assertEqual(plan.slot.domain, "ancient world history")
        self.assertTrue(plan.slot.standard.startswith("CA HSS 6."))
        self.assertGreaterEqual(len(plan.slot.required_content), 3)

    def test_science_curriculum_changes_with_grade(self):
        grade_five = reading_guardrail.prepare(
            SCIENCE_READING, "2099-01-01", 5, "science"
        )
        grade_eight = reading_guardrail.prepare(
            SCIENCE_READING, "2099-01-01", 8, "science"
        )

        self.assertNotEqual(grade_five.slot.standard, grade_eight.slot.standard)
        self.assertNotEqual(grade_five.slot.learning_goal, grade_eight.slot.learning_goal)

    def test_reading_guardrail_rejects_vocabulary_missing_from_passage(self):
        plan = reading_guardrail.prepare(
            ENGLISH_READING, "2099-01-01", 6, "history"
        )
        task = {
            "passage": {"title": "History", "text": "history " * 500},
            "vocabulary": [{"word": "artifact"}] + [
                {"word": "history"} for _ in range(7)
            ],
            "questions": [
                {
                    "id": f"q_{index}",
                    "type": "detail",
                    "skill": "evidence",
                    "question": "What happened?",
                    "answer": "An event happened.",
                }
                for index in range(8)
            ],
        }

        errors = reading_guardrail.validate(ENGLISH_READING, task, plan)

        self.assertIn("vocabulary word not used in passage: artifact", errors)

    def test_reading_guardrail_commit_stores_concept_memory(self):
        original_path = reading_guardrail_store.MEMORY_PATH
        with tempfile.TemporaryDirectory() as tmp:
            try:
                reading_guardrail_store.MEMORY_PATH = Path(tmp) / "concepts.json"
                plan = reading_guardrail.prepare(
                    ENGLISH_READING,
                    "2099-01-01",
                    6,
                    "main idea",
                )
                task = {
                    "passage": {
                        "title": "A New Tool",
                        "text": "w0 w1 w2 w3 w4 w5 w6 w7 " + "word " * 492,
                    },
                    "vocabulary": [{"word": f"w{i}"} for i in range(8)],
                    "questions": [
                        {
                            "id": f"q_{i:03d}",
                            "type": "detail" if i == 1 else "main_idea",
                            "skill": "text evidence",
                            "question": f"Question {i}?",
                            "answer": f"Answer {i}",
                        }
                        for i in range(1, 9)
                    ],
                    "metadata": {},
                }

                self.assertEqual(reading_guardrail.validate(ENGLISH_READING, task, plan), [])
                reading_guardrail.commit(ENGLISH_READING, "2099-01-01", task, plan)

                records = reading_guardrail_store.load_records()
                self.assertEqual(len(records), 1)
                self.assertEqual(records[0]["concept"], plan.core_concept)
                self.assertEqual(len(records[0]["embedding"]), reading_guardrail.EMBED_DIM)
                self.assertEqual(
                    task["metadata"]["reading_guardrail"]["external_passage_id"],
                    plan.external_passage_id,
                )
            finally:
                reading_guardrail_store.MEMORY_PATH = original_path

    def test_writing_meta_tracks_two_revision_rounds(self):
        meta = writing_store.build_meta({"task_version": 2})

        self.assertEqual(set(meta), {"draft", "revision"})
        self.assertEqual(meta["draft"]["skill"], "writing_structure_evidence")
        self.assertEqual(meta["revision"]["skill"], "writing_language_revision")

    def test_writing_task_normalization_sets_50_word_structure(self):
        task = {"writing_mode": "opinion", "writing_prompt": "Should school begin later?"}

        writing_service._normalize_task(task)

        self.assertEqual(task["target_words"], 50)
        self.assertEqual(task["target_range"], [45, 65])
        self.assertEqual(len(task["structure"]), 3)
        self.assertEqual(
            [item["round"] for item in task["practice"]["revision_rounds"]],
            [1, 2],
        )
        self.assertNotIn("focus_words", task)

    def test_writing_guardrail_rejects_repeated_prompt(self):
        sample = (
            "Ancient farmers settled near rivers because water helped them grow crops. "
            "Reliable harvests created food surpluses, so some people became builders, "
            "traders, or leaders. As villages expanded, communities developed rules and "
            "shared projects. These changes show how agriculture helped settlements grow "
            "into more complex societies over time."
        )
        task = {
            "writing_mode": "opinion",
            "writing_prompt": "Should students read history every day?",
            "source": {"title": "", "text": ""},
            "structure": [{}, {}, {}],
            "practice": {
                "revision_rounds": [{"round": 1}, {"round": 2}],
                "sample_response": sample,
            },
        }
        history = {"avoid_prompts": ["Should students read history every day?"]}

        errors = writing_service._validate_task(task, history, "opinion")

        self.assertIn("writing prompt is too similar to recent writing", errors)

    def test_writing_generation_retries_repeated_prompt(self):
        original_root = daily_task_store.TASK_ROOT

        class FakeWritingProvider:
            name = "Fake Writing"

            def __init__(self, invalid_task, valid_task):
                self.calls = 0
                self.invalid_task = invalid_task
                self.valid_task = valid_task

            def complete(self, system: str, user: str, max_tokens: int = 7000) -> str:
                self.calls += 1
                return json.dumps(self.invalid_task if self.calls == 1 else self.valid_task)

        try:
            with tempfile.TemporaryDirectory() as tmp:
                daily_task_store.TASK_ROOT = Path(tmp)
                writing_store.save_task("2099-01-01", {
                    "date": "2099-01-01",
                    "task_version": 2,
                    "writing_prompt": "Should students read history every day?",
                    "practice": {"sample_response": "old sample"},
                })
                sample = (
                    "Ancient farmers settled near rivers because water helped them grow crops. "
                    "Reliable harvests created food surpluses, so some people became builders, "
                    "traders, or leaders. As villages expanded, communities developed rules and "
                    "shared projects. These changes show how agriculture helped settlements grow "
                    "into more complex societies over time."
                )
                invalid = {
                    "writing_mode": "opinion",
                    "writing_prompt": "Should students read history every day?",
                    "source": {"title": "", "text": ""},
                    "practice": {"sample_response": sample},
                }
                valid = {
                    "writing_mode": "opinion",
                    "writing_prompt": "Which ancient invention had the greatest impact on daily life?",
                    "source": {"title": "", "text": ""},
                    "practice": {"sample_response": sample},
                }
                provider = FakeWritingProvider(invalid, valid)

                with patch("services.writing_service._ensure_pdfs"), patch(
                    "services.writing_service._writing_context",
                    return_value={"writing_mode": "opinion", "source": {"title": "", "text": ""}},
                ):
                    task = writing_service.generate("2099-01-02", provider)

                self.assertEqual(provider.calls, 2)
                self.assertEqual(task["writing_prompt"], valid["writing_prompt"])
                self.assertEqual(task["target_words"], 50)
                self.assertTrue(task["writing_guardrail"]["vocabulary_is_separate"])
                self.assertEqual(task["writing_guardrail"]["history_days"], 30)
        finally:
            daily_task_store.TASK_ROOT = original_root

    def test_writing_review_uses_actual_draft_and_persists_feedback(self):
        original_root = daily_task_store.TASK_ROOT

        class FakeReviewProvider:
            name = "Fake Review"

            def __init__(self):
                self.user = ""

            def complete(self, system: str, user: str, max_tokens: int = 1800) -> str:
                self.user = user
                return json.dumps({
                    "round": 1,
                    "focus": "structure_and_evidence",
                    "strength": "The claim is direct.",
                    "answer_feedback": "Keep the claim.",
                    "evidence_feedback": "Add one precise detail.",
                    "next_step": "Add the date from the passage.",
                    "ready_for_round_2": True,
                })

        try:
            with tempfile.TemporaryDirectory() as tmp:
                daily_task_store.TASK_ROOT = Path(tmp)
                provider = FakeReviewProvider()
                task = {
                    "date": "2099-01-01",
                    "grade_level": 6,
                    "writing_mode": "opinion",
                    "writing_prompt": "Which invention mattered most?",
                    "source": {"title": "", "text": ""},
                }
                draft = "I think writing mattered most because it preserved laws and ideas for later generations."

                feedback = writing_service.review_draft(task, draft, 1, provider)

                self.assertEqual(feedback["round"], 1)
                self.assertIn(draft, provider.user)
                self.assertEqual(
                    writing_store.load_submission("2099-01-01")["round_1"]["draft"],
                    draft,
                )
        finally:
            daily_task_store.TASK_ROOT = original_root

    def test_math_guardrail_checks_unicode_arithmetic_answer(self):
        homework = {
            "parts": {
                "part1": [{
                    "id": "p1_001",
                    "question": "5² × 2³ - 100",
                    "answer": "300",
                }],
                "part2": [],
                "part3": [],
            }
        }

        errors = math_guardrail.validate(homework, "standard")

        self.assertTrue(any("expected 100" in error for error in errors))

    def test_math_guardrail_accepts_equivalent_mixed_number_answer(self):
        homework = {
            "parts": {
                "part1": [{
                    "id": "p1_001",
                    "question": "3/4 + 2/3",
                    "answer": "1 5/12",
                }],
                "part2": [],
                "part3": [],
            }
        }

        self.assertEqual(math_guardrail.validate(homework, "standard"), [])

    def test_math_challenge_guardrail_keeps_existing_part_counts(self):
        homework = {"parts": {"part1": [], "part2": [], "part3": []}}

        errors = math_guardrail.validate(homework, "challenge")

        self.assertIn("part1 must contain exactly 20 questions", errors)
        self.assertIn("part2 must contain exactly 12 questions", errors)
        self.assertIn("part3 must contain exactly 3 questions", errors)

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
