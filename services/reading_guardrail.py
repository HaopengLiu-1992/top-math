import hashlib
import math
import re
from dataclasses import asdict, dataclass

from domain.daily_task import SCIENCE_READING, TaskScope
from storage import reading_guardrail_store

EMBED_DIM = 64
AVOID_TOP_K = 4
DUPLICATE_THRESHOLD = 0.86


@dataclass(frozen=True)
class ReadingSlot:
    grade: int
    domain: str
    topic: str
    subtopic: str
    text_type: str
    skill: str


@dataclass(frozen=True)
class ReadingPlan:
    slot: ReadingSlot
    core_concept: str
    avoid_concepts: list[str]
    external_passage_id: str

    def as_prompt_context(self) -> dict:
        return {
            "slot": asdict(self.slot),
            "core_concept": self.core_concept,
            "avoid_concepts": self.avoid_concepts,
            "external_passage_id": self.external_passage_id,
        }


ENGLISH_SLOTS = [
    ("literary", "relationships", "helping a new classmate", "realistic fiction", "character motivation"),
    ("literary", "identity", "learning from a mistake", "realistic fiction", "theme"),
    ("literary", "community", "solving a neighborhood problem", "realistic fiction", "plot and conflict"),
    ("informational", "technology", "how an invention changes daily life", "expository", "main idea"),
    ("informational", "history", "children's lives in a past time period", "historical nonfiction", "compare and contrast"),
    ("informational", "culture", "a tradition and what it teaches", "expository", "author's purpose"),
    ("argument", "school life", "whether students should have class jobs", "opinion article", "claim and evidence"),
    ("argument", "environment", "ways students can reduce waste", "persuasive nonfiction", "evidence"),
]

SCIENCE_SLOTS = [
    ("life science", "ecosystems", "organisms depending on each other", "science nonfiction", "cause and effect"),
    ("life science", "adaptations", "animal traits that support survival", "science nonfiction", "evidence"),
    ("earth science", "weather and climate", "how weather patterns affect communities", "science nonfiction", "main idea"),
    ("earth science", "water cycle", "movement of water through Earth systems", "science nonfiction", "sequence"),
    ("physical science", "forces and motion", "how pushes and pulls change movement", "science nonfiction", "cause and effect"),
    ("physical science", "energy", "energy transfer in everyday systems", "science nonfiction", "explanation"),
    ("science practice", "investigation", "testing a fair experiment", "science investigation", "claim evidence reasoning"),
    ("science practice", "data", "using observations to support a conclusion", "data-based article", "data interpretation"),
]

CONCEPT_TEMPLATES = [
    "{subtopic} in a school setting",
    "{subtopic} during an outdoor activity",
    "{subtopic} through a student investigation",
    "{subtopic} in a family or community example",
    "{subtopic} using a surprising real-world problem",
    "{subtopic} from the point of view of a careful observer",
]


def prepare(scope: TaskScope, date_str: str, grade_level: int, focus: str) -> ReadingPlan:
    slot = _select_slot(scope, date_str, grade_level, focus)
    records = reading_guardrail_store.load_records()
    candidates = _concept_candidates(slot)
    ranked = _rank_similar(candidates, records, scope, grade_level)
    core_concept = _first_non_duplicate(ranked)
    avoid_concepts = [
        item["concept"] for item in _top_similar_records(core_concept, records, scope, grade_level)
    ][:AVOID_TOP_K]
    external_id = _external_passage_id(scope, date_str, grade_level, core_concept)
    return ReadingPlan(slot=slot, core_concept=core_concept,
                       avoid_concepts=avoid_concepts, external_passage_id=external_id)


def validate(scope: TaskScope, task: dict, plan: ReadingPlan) -> list[str]:
    errors: list[str] = []
    passage = task.get("passage") or {}
    questions = task.get("questions") or []
    vocabulary = task.get("vocabulary") or []

    if not passage.get("title") or not passage.get("text"):
        errors.append("missing passage title/text")
    if len(vocabulary) != 8:
        errors.append("expected 8 vocabulary words")
    if len(questions) != 8:
        errors.append("expected 8 questions")

    grade = plan.slot.grade
    actual_words = len(_tokens(passage.get("text", "")))
    if grade <= 6 and not 350 <= actual_words <= 750:
        errors.append(f"passage word count out of grade 5-6 range: {actual_words}")
    if grade >= 7 and not 550 <= actual_words <= 950:
        errors.append(f"passage word count out of grade 7-8 range: {actual_words}")

    if not any((q.get("type") or "").lower() in {"detail", "evidence", "claim_evidence"}
               or "evidence" in (q.get("skill") or "").lower()
               for q in questions):
        errors.append("missing evidence/detail question")

    if _is_duplicate(scope, grade, plan.core_concept):
        errors.append("core concept duplicates prior reading memory")

    return errors


def commit(scope: TaskScope, date_str: str, task: dict, plan: ReadingPlan):
    metadata = task.setdefault("metadata", {})
    metadata["reading_guardrail"] = plan.as_prompt_context()
    reading_guardrail_store.append_record({
        "external_passage_id": plan.external_passage_id,
        "date": date_str,
        "scope": scope.key,
        "subject": scope.subject,
        "grade": plan.slot.grade,
        "slot": asdict(plan.slot),
        "concept": plan.core_concept,
        "embedding": _embed(plan.core_concept),
        "passage_title": (task.get("passage") or {}).get("title"),
        "question_skills": [q.get("skill") for q in task.get("questions", [])],
    })


def _select_slot(scope: TaskScope, date_str: str, grade: int, focus: str) -> ReadingSlot:
    slots = SCIENCE_SLOTS if scope == SCIENCE_READING else ENGLISH_SLOTS
    seed = f"{scope.key}|{date_str}|{grade}|{focus}".encode()
    idx = int(hashlib.sha256(seed).hexdigest()[:8], 16) % len(slots)
    domain, topic, subtopic, text_type, skill = slots[idx]
    return ReadingSlot(grade=grade, domain=domain, topic=topic,
                       subtopic=subtopic, text_type=text_type, skill=skill)


def _concept_candidates(slot: ReadingSlot) -> list[str]:
    return [template.format(subtopic=slot.subtopic) for template in CONCEPT_TEMPLATES]


def _rank_similar(candidates: list[str], records: list[dict],
                  scope: TaskScope, grade: int) -> list[dict]:
    return [{
        "concept": concept,
        "similarity": max(
            [_cosine(_embed(concept), record.get("embedding", []))
             for record in records
             if record.get("scope") == scope.key and record.get("grade") == grade] or [0.0]
        ),
    } for concept in candidates]


def _first_non_duplicate(ranked: list[dict]) -> str:
    ranked = sorted(ranked, key=lambda item: item["similarity"])
    for item in ranked:
        if item["similarity"] < DUPLICATE_THRESHOLD:
            return item["concept"]
    return ranked[0]["concept"]


def _top_similar_records(concept: str, records: list[dict],
                         scope: TaskScope, grade: int) -> list[dict]:
    vector = _embed(concept)
    scored = []
    for record in records:
        if record.get("scope") != scope.key or record.get("grade") != grade:
            continue
        scored.append({
            "concept": record.get("concept", ""),
            "similarity": _cosine(vector, record.get("embedding", [])),
        })
    return sorted(scored, key=lambda item: item["similarity"], reverse=True)


def _is_duplicate(scope: TaskScope, grade: int, concept: str) -> bool:
    return any(item["similarity"] >= DUPLICATE_THRESHOLD
               for item in _top_similar_records(concept, reading_guardrail_store.load_records(), scope, grade))


def _embed(text: str) -> list[float]:
    vector = [0.0] * EMBED_DIM
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode()).digest()
        idx = digest[0] % EMBED_DIM
        sign = 1 if digest[1] % 2 == 0 else -1
        vector[idx] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _external_passage_id(scope: TaskScope, date_str: str, grade: int, concept: str) -> str:
    digest = hashlib.sha256(f"{scope.key}|{date_str}|{grade}|{concept}".encode()).hexdigest()[:12]
    return f"{scope.subject}-{scope.task_type}-{date_str}-{digest}"
