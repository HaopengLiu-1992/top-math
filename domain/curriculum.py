from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from domain.learning_context import LearningContext


@dataclass(frozen=True)
class CurriculumTopic:
    id: str
    subject: str
    grade_level: int
    domain: str
    title: str
    standard: str
    description: str
    prerequisites: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    lesson_types: list[str] = field(default_factory=list)
    question_types: list[str] = field(default_factory=list)

    def to_prompt_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "grade_level": self.grade_level,
            "domain": self.domain,
            "title": self.title,
            "standard": self.standard,
            "description": self.description,
            "prerequisites": self.prerequisites,
            "skills": self.skills,
            "lesson_types": self.lesson_types,
            "question_types": self.question_types,
        }


@dataclass(frozen=True)
class CurriculumScope:
    subject: str
    grade_level: int
    standards_body: str
    topics: list[CurriculumTopic]


class CurriculumProvider(ABC):
    @abstractmethod
    def subject(self) -> str:
        ...

    @abstractmethod
    def standards_body(self) -> str:
        ...

    @abstractmethod
    def supported_grades(self) -> list[int]:
        ...

    @abstractmethod
    def get_scope(self, grade_level: int) -> CurriculumScope:
        ...

    @abstractmethod
    def get_topic(self, topic_id: str) -> CurriculumTopic:
        ...

    @abstractmethod
    def next_topic(self, context: LearningContext) -> CurriculumTopic:
        ...
