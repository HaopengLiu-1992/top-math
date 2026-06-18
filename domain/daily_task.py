from dataclasses import dataclass


@dataclass(frozen=True)
class TaskScope:
    subject: str
    task_type: str

    @property
    def key(self) -> str:
        return f"{self.subject}/{self.task_type}"


MATH_HOMEWORK = TaskScope(subject="math", task_type="homework")
ENGLISH_VOCABULARY = TaskScope(subject="english", task_type="vocabulary")
ENGLISH_READING = TaskScope(subject="english", task_type="reading")
SCIENCE_READING = TaskScope(subject="science", task_type="reading")

ALL_TASK_SCOPES = [
    MATH_HOMEWORK,
    ENGLISH_VOCABULARY,
    ENGLISH_READING,
    SCIENCE_READING,
]

TASK_LABELS = {
    MATH_HOMEWORK: "Math Homework",
    ENGLISH_VOCABULARY: "Academic Vocabulary",
    ENGLISH_READING: "English Reading",
    SCIENCE_READING: "Science Reading",
}
