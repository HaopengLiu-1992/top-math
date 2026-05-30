import json
from functools import lru_cache
from pathlib import Path

from domain.curriculum import CurriculumProvider, CurriculumScope, CurriculumTopic
from domain.learning_context import LearningContext

_BASE_DIR = Path(__file__).parent


class MathCommonCoreProvider(CurriculumProvider):
    def subject(self) -> str:
        return "math"

    def standards_body(self) -> str:
        return "Common Core State Standards"

    def supported_grades(self) -> list[int]:
        return [5, 6, 7, 8]

    def get_scope(self, grade_level: int) -> CurriculumScope:
        if grade_level not in self.supported_grades():
            raise ValueError(f"Math Common Core grade {grade_level} is not configured")

        data = _load_grade_data(grade_level)
        topics = [_topic_from_dict(item, data) for item in data["topics"]]
        return CurriculumScope(
            subject=data["subject"],
            grade_level=data["grade_level"],
            standards_body=data["standards_body"],
            topics=topics,
        )

    def get_topic(self, topic_id: str) -> CurriculumTopic:
        for grade in self.supported_grades():
            for topic in self.get_scope(grade).topics:
                if topic.id == topic_id:
                    return topic
        raise ValueError(f"Unknown math topic id {topic_id!r}")

    def next_topic(self, context: LearningContext) -> CurriculumTopic:
        scope = self.get_scope(context.grade_level)
        recent = set(context.recent_topics)
        for topic in scope.topics:
            if topic.id not in recent and topic.standard not in recent:
                return topic
        return scope.topics[0]


@lru_cache(maxsize=None)
def _load_grade_data(grade_level: int) -> dict:
    path = _BASE_DIR / f"grade{grade_level}.json"
    return json.loads(path.read_text())


def _topic_from_dict(item: dict, data: dict) -> CurriculumTopic:
    return CurriculumTopic(
        id=item["id"],
        subject=data["subject"],
        grade_level=data["grade_level"],
        domain=item["domain"],
        title=item["title"],
        standard=item["standard"],
        description=item["description"],
        prerequisites=item.get("prerequisites", []),
        skills=item.get("skills", []),
        lesson_types=item.get("lesson_types", ["intro", "reteach", "challenge"]),
        question_types=item.get("question_types", []),
    )
