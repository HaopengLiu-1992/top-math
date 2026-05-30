import json
import tempfile
import unittest
from pathlib import Path

from curriculum.registry import get_provider
from domain.learning_context import LearningContext
from prompts import homework_prompt
from services import curriculum_service
from services.generator import _generate_with_retry
from storage import lesson_store


class CourseArchitectureTests(unittest.TestCase):
    def test_math_provider_supports_grades_5_to_8(self):
        provider = get_provider("math")

        self.assertEqual(provider.supported_grades(), [5, 6, 7, 8])
        for grade in provider.supported_grades():
            scope = provider.get_scope(grade)
            self.assertEqual(scope.subject, "math")
            self.assertEqual(scope.grade_level, grade)
            self.assertGreater(len(scope.topics), 0)

    def test_curriculum_service_resolves_manual_and_auto_topic(self):
        manual = LearningContext(grade_level=6, target_topic_id="6.RP.A.3")
        self.assertEqual(curriculum_service.resolve_topic(manual).id, "6.RP.A.3")

        auto = LearningContext(grade_level=6, recent_topics=["6.RP.A.1"])
        self.assertEqual(curriculum_service.resolve_topic(auto).id, "6.RP.A.3")

    def test_lesson_store_round_trip(self):
        original_root = lesson_store.LESSON_ROOT
        with tempfile.TemporaryDirectory() as tmp:
            try:
                lesson_store.LESSON_ROOT = Path(tmp)
                lesson = {"title": "Ratio concepts", "objective": "Understand ratios"}

                path = lesson_store.save_lesson(lesson, "math", 6, "6.RP.A.1")
                self.assertTrue(path.exists())
                self.assertEqual(
                    lesson_store.load_lesson("math", 6, "6.RP.A.1"),
                    lesson,
                )
            finally:
                lesson_store.LESSON_ROOT = original_root

    def test_homework_prompt_includes_course_context_and_cache(self):
        topic = curriculum_service.resolve_topic(
            LearningContext(grade_level=6, target_topic_id="6.RP.A.1")
        )
        context = LearningContext(
            grade_level=6,
            mode="lesson_practice",
            include_lesson=True,
            include_hints=False,
            target_topic_id=topic.id,
        )

        prompt = homework_prompt.user_prompt(
            10,
            "2099-01-01",
            [],
            set(),
            context=context,
            topic=topic,
            cached_lesson={"title": "Cached ratio lesson"},
        )

        self.assertIn("Grade level: 6", prompt)
        self.assertIn("Include lesson: True", prompt)
        self.assertIn("Include hints: False", prompt)
        self.assertIn("6.RP.A.1", prompt)
        self.assertIn("Cached ratio lesson", prompt)

    def test_generator_retry_uses_course_context_and_long_output_budget(self):
        topic = curriculum_service.resolve_topic(
            LearningContext(grade_level=6, target_topic_id="6.RP.A.1")
        )
        context = LearningContext(grade_level=6, target_topic_id=topic.id)
        provider = _FakeProvider()

        homework = _generate_with_retry(
            10,
            "2099-01-01",
            [],
            set(),
            provider,
            context=context,
            topic=topic,
        )

        self.assertEqual(homework["grade_level"], 6)
        self.assertEqual(provider.max_tokens_seen, 12000)
        self.assertIn("6.RP.A.1", provider.user_prompt_seen)


class _FakeProvider:
    name = "Fake"

    def __init__(self):
        self.max_tokens_seen = None
        self.user_prompt_seen = ""

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        self.max_tokens_seen = max_tokens
        self.user_prompt_seen = user
        return json.dumps({
            "day": 10,
            "date": "2099-01-01",
            "subject": "math",
            "grade_level": 6,
            "mode": "lesson_practice",
            "target_topic": {
                "id": "6.RP.A.1",
                "title": "Ratio concepts",
                "standard": "6.RP.A.1",
                "domain": "Ratios and Proportional Relationships",
            },
            "estimated_minutes": 30,
            "encouragement": "Nice work.",
            "lesson": None,
            "parts": {
                "part1": [
                    {
                        "id": "p1_001",
                        "question": "Find an equivalent ratio to 2:3.",
                        "answer": "4:6",
                        "fingerprint": "6.RP.A.1|ratio|2:3",
                        "topic": "6.RP.A.1",
                    }
                ],
                "part2": [],
                "part3": [],
            },
            "weekly_challenge": None,
        })


if __name__ == "__main__":
    unittest.main()
