from dataclasses import dataclass, field


@dataclass(frozen=True)
class LearningContext:
    student_id: str = "jessie"
    subject: str = "math"
    grade_level: int = 6
    mode: str = "lesson_practice"
    include_lesson: bool = True
    include_hints: bool = True
    target_topic_id: str | None = None
    difficulty_policy: str = "advanced"
    recent_topics: list[str] = field(default_factory=list)

    def normalized_subject(self) -> str:
        return self.subject.strip().lower()
