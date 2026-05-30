from domain.curriculum import CurriculumTopic
from domain.learning_context import LearningContext
from storage import lesson_store


def load_cached_lesson(context: LearningContext, topic: CurriculumTopic,
                       lesson_type: str = "intro") -> dict | None:
    return lesson_store.load_lesson(
        context.subject,
        context.grade_level,
        topic.id,
        lesson_type=lesson_type,
    )


def cache_lesson_from_homework(homework: dict, context: LearningContext,
                               topic: CurriculumTopic,
                               lesson_type: str = "intro") -> dict | None:
    lesson = homework.get("lesson")
    if not lesson:
        return None

    lesson = dict(lesson)
    lesson.setdefault("subject", context.subject)
    lesson.setdefault("grade_level", context.grade_level)
    lesson.setdefault("topic_id", topic.id)
    lesson.setdefault("topic_title", topic.title)
    lesson.setdefault("standard", topic.standard)
    lesson_store.save_lesson(
        lesson,
        context.subject,
        context.grade_level,
        topic.id,
        lesson_type=lesson_type,
    )
    return lesson
