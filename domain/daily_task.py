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
