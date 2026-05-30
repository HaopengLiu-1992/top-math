from curriculum.registry import get_provider
from domain.curriculum import CurriculumScope, CurriculumTopic
from domain.learning_context import LearningContext


def get_scope(subject: str, grade_level: int) -> CurriculumScope:
    return get_provider(subject).get_scope(grade_level)


def list_topics(subject: str, grade_level: int) -> list[CurriculumTopic]:
    return get_scope(subject, grade_level).topics


def resolve_topic(context: LearningContext) -> CurriculumTopic:
    provider = get_provider(context.subject)
    if context.target_topic_id:
        return provider.get_topic(context.target_topic_id)
    return provider.next_topic(context)
