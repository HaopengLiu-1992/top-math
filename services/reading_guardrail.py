import hashlib
import math
import re
from dataclasses import asdict, dataclass
from datetime import date

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
    standard: str
    learning_goal: str
    required_content: tuple[str, ...]


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


HISTORY_SLOTS_BY_GRADE = {
    5: [
        ("US history", "Indigenous societies", "diverse societies before European contact", "historical nonfiction", "compare and contrast", "CA HSS 5.1", "Compare how geography shaped Indigenous societies.", ("regional diversity", "geography", "adaptation")),
        ("US history", "European exploration", "motives and consequences of exploration", "historical nonfiction", "cause and effect", "CA HSS 5.2", "Explain competing motives and consequences of exploration.", ("trade routes", "colonization", "Indigenous peoples")),
        ("US history", "Colonial regions", "New England, Middle, and Southern colonies", "historical nonfiction", "compare and contrast", "CA HSS 5.4", "Compare colonial regions using economic and geographic evidence.", ("regional economies", "labor", "geography")),
        ("US history", "American Revolution", "causes and perspectives in the Revolution", "primary-and-secondary source set", "claim and evidence", "CA HSS 5.5", "Use sources to explain causes and differing perspectives.", ("taxation", "representation", "Patriots and Loyalists")),
        ("US history", "US Constitution", "the Constitution and branches of government", "historical nonfiction", "main idea and evidence", "CA HSS 5.7", "Explain how the Constitution organizes and limits power.", ("three branches", "checks and balances", "rights")),
    ],
    6: [
        ("ancient world history", "Early humans", "the Paleolithic era and agricultural revolution", "historical nonfiction", "cause and effect", "CA HSS 6.1", "Explain how agriculture changed settlement and society.", ("Paleolithic communities generally lived by hunting and gathering", "domestication supported more permanent settlements", "food surpluses encouraged population growth and specialized work")),
        ("ancient world history", "Mesopotamia", "river valleys, city-states, and written law", "primary-and-secondary source set", "cause and effect", "CA HSS 6.2", "Connect geography and institutions to the growth of Mesopotamian societies.", ("the Tigris and Euphrates supported irrigation but also brought unpredictable floods", "Mesopotamia included independent city-states rather than one permanent unified state", "cuneiform was used for records, literature, and law")),
        ("ancient world history", "Egypt and Kush", "the Nile, government, and cultural exchange", "historical nonfiction", "compare and contrast", "CA HSS 6.2", "Compare how Nile geography shaped Egypt and Kush.", ("seasonal Nile flooding supported agriculture", "pharaohs combined political and religious authority", "Egypt and Kush influenced each other through trade, conflict, and cultural exchange")),
        ("ancient world history", "Ancient Hebrews", "belief, law, and historical traditions", "primary-and-secondary source set", "source and context", "CA HSS 6.3", "Explain major ideas and evaluate the context of historical sources.", ("Judaism developed a lasting monotheistic tradition", "religious and ethical laws shaped community life", "diaspora describes the dispersal of Jewish communities beyond their ancestral homeland")),
        ("ancient world history", "Ancient Greece", "polis, democracy, and Persian influence", "primary-and-secondary source set", "compare and contrast", "CA HSS 6.4", "Compare Greek political systems and cultural achievements.", ("Greek communities were organized as separate poleis", "Athens practiced a limited form of direct democracy that excluded much of the population", "Sparta emphasized military organization and had a different political system from Athens")),
        ("ancient world history", "Ancient India", "Indus society, belief systems, and empires", "historical nonfiction", "chronology and evidence", "CA HSS 6.5", "Trace continuity and change across early Indian civilizations.", ("Indus cities show evidence of planned streets and drainage", "Hinduism and Buddhism developed in ancient India but are distinct traditions", "the Maurya Empire unified much of the subcontinent")),
        ("ancient world history", "Ancient China", "dynasties, philosophies, and technology", "primary-and-secondary source set", "cause and effect", "CA HSS 6.6", "Explain how ideas and institutions shaped early China.", ("the Mandate of Heaven was used to explain dynastic rule and change", "Confucianism emphasized ethical relationships and responsible government", "Han government and innovation strengthened a large empire")),
        ("ancient world history", "Ancient Rome", "republic, empire, and Roman legacy", "primary-and-secondary source set", "claim and evidence", "CA HSS 6.7", "Use evidence to explain Rome's expansion and lasting influence.", ("the Roman Republic divided power among institutions but citizenship was limited", "Rome later became an empire controlling lands around the Mediterranean", "Roman law, language, roads, and engineering had lasting influence")),
    ],
    7: [
        ("medieval and early modern history", "Roman legacy", "the fall of Rome and Byzantine continuity", "historical nonfiction", "continuity and change", "CA HSS 7.1", "Explain continuity and change after the western Roman Empire.", ("Byzantine Empire", "Constantinople", "Roman law")),
        ("medieval and early modern history", "Islamic civilizations", "the rise and spread of Islam", "primary-and-secondary source set", "cause and effect", "CA HSS 7.2", "Explain the growth and achievements of Islamic civilizations.", ("Arabian Peninsula", "caliphates", "trade and scholarship")),
        ("medieval and early modern history", "Medieval China", "Tang and Song government, trade, and innovation", "historical nonfiction", "cause and effect", "CA HSS 7.3", "Connect institutions and innovation to social change.", ("civil service", "Silk Roads", "printing and navigation")),
        ("medieval and early modern history", "West Africa", "Ghana and Mali in trans-Saharan trade", "historical nonfiction", "claim and evidence", "CA HSS 7.4", "Use evidence to explain trade and state growth.", ("gold and salt", "Mansa Musa", "Timbuktu")),
        ("medieval and early modern history", "Medieval Europe", "feudalism, towns, and changing institutions", "primary-and-secondary source set", "continuity and change", "CA HSS 7.6", "Explain how institutions and daily life changed over time.", ("feudal obligations", "manors", "Magna Carta")),
        ("medieval and early modern history", "Renaissance and Reformation", "humanism, printing, and religious change", "primary-and-secondary source set", "source and context", "CA HSS 7.8-7.9", "Evaluate how ideas and technologies produced change.", ("humanism", "printing press", "Reformation")),
    ],
    8: [
        ("US history", "Founding era", "revolutionary ideas and the Constitution", "primary-and-secondary source set", "claim and evidence", "CA HSS 8.1-8.2", "Evaluate how founding principles shaped government.", ("natural rights", "federalism", "Bill of Rights")),
        ("US history", "Early republic", "political parties and expanding democracy", "historical nonfiction", "cause and effect", "CA HSS 8.3-8.4", "Explain political change in the early republic.", ("political parties", "suffrage", "judicial review")),
        ("US history", "Westward expansion", "expansion and its consequences for different groups", "primary-and-secondary source set", "multiple perspectives", "CA HSS 8.8", "Compare perspectives on territorial expansion.", ("Manifest Destiny", "Indigenous displacement", "Mexican Cession")),
        ("US history", "Civil War", "sectional conflict, war, and emancipation", "primary-and-secondary source set", "cause and effect", "CA HSS 8.10", "Use evidence to explain causes and turning points.", ("slavery", "sectionalism", "Emancipation Proclamation")),
        ("US history", "Reconstruction and industry", "Reconstruction, migration, and industrial growth", "historical nonfiction", "continuity and change", "CA HSS 8.11-8.12", "Analyze gains, limits, and economic transformation.", ("Reconstruction amendments", "sharecropping", "industrialization")),
    ],
}

SCIENCE_SLOTS_BY_GRADE = {
    5: [
        ("physical science", "matter", "particles, properties, and conservation of matter", "phenomenon-and-data article", "model and evidence", "5-PS1-1/2/3", "Use particle models and measurements to explain matter.", ("matter is made of particles", "properties identify substances", "mass is conserved")),
        ("life science", "plant matter", "where plants get materials for growth", "science explanation", "claim evidence reasoning", "5-LS1-1", "Explain that plant matter comes chiefly from air and water.", ("air", "water", "plant growth")),
        ("life science", "ecosystem matter", "movement of matter through food webs", "model-based article", "systems reasoning", "5-LS2-1", "Model matter movement among organisms and the environment.", ("producers", "consumers", "decomposers")),
        ("earth science", "Earth systems", "interactions among geosphere, hydrosphere, atmosphere, and biosphere", "phenomenon-and-data article", "cause and effect", "5-ESS2-1", "Explain an interaction between two Earth systems.", ("Earth systems", "water", "living things")),
        ("space science", "stars and sunlight", "brightness of stars and daily shadow patterns", "data-based article", "data interpretation", "5-ESS1-1/2", "Use data to explain apparent brightness and repeating patterns.", ("distance", "apparent brightness", "shadows")),
    ],
    6: [
        ("life science", "cells and body systems", "cells, tissues, organs, and interacting body systems", "model-based article", "systems reasoning", "MS-LS1-1/3", "Use evidence and models to explain levels of organization.", ("living organisms are made of cells", "specialized cells form tissues and organs with particular functions", "body systems interact rather than working independently")),
        ("earth science", "weather and climate", "air masses, unequal heating, and regional climate", "phenomenon-and-data article", "cause and effect", "MS-ESS2-5/6", "Use data and energy flow to explain weather and climate patterns.", ("unequal solar heating helps drive atmospheric circulation", "interacting air masses can produce weather changes", "latitude, landforms, and ocean circulation influence regional climate")),
        ("earth science", "plate tectonics", "patterns in earthquakes, volcanoes, fossils, and rocks", "map-and-evidence article", "pattern and evidence", "MS-ESS2-2/3", "Use geologic patterns as evidence for plate motion.", ("earthquakes and volcanoes cluster near many plate boundaries", "matching fossils and rocks across continents support past plate motion", "different boundary motions produce different geologic effects")),
        ("physical science", "thermal energy", "particle motion and energy transfer", "investigation article", "model and evidence", "MS-PS3-3/4", "Explain thermal energy transfer with particle models.", ("temperature relates to average particle motion", "thermal energy transfers from warmer matter to cooler matter", "materials differ in how quickly they conduct thermal energy")),
        ("environmental science", "human impacts", "resource use and changes to Earth systems", "data-based argument", "claim evidence reasoning", "MS-ESS3-3/4", "Evaluate evidence about human impacts and possible solutions.", ("resource use can alter Earth systems", "population and consumption both affect environmental impact", "design solutions should be evaluated with evidence and trade-offs")),
        ("science practice", "experimental design", "variables, repeated trials, accuracy, and precision", "science investigation", "data interpretation", "MS-ETS1-3", "Evaluate the quality of an investigation and its data.", ("the independent variable is deliberately changed and the dependent variable is measured", "repeated trials help reveal variation and improve reliability", "accuracy and precision describe different qualities of measurement")),
    ],
    7: [
        ("physical science", "chemical reactions", "atoms rearranging while mass is conserved", "phenomenon-and-data article", "model and evidence", "MS-PS1-2/5", "Use evidence and models to explain chemical reactions.", ("reactants and products", "atom rearrangement", "conservation of mass")),
        ("life science", "ecosystem dynamics", "energy flow, matter cycling, and population change", "model-based article", "systems reasoning", "MS-LS2-1/3/4", "Analyze ecosystem interactions and changes.", ("food webs", "matter cycling", "population limits")),
        ("life science", "genetics", "genes, proteins, traits, and environmental influence", "science explanation", "cause and effect", "MS-LS3-1/2", "Explain how genetic information relates to inherited traits.", ("genes", "proteins", "variation")),
        ("earth science", "geologic processes", "rock cycling and changes to Earth's surface", "phenomenon-and-data article", "cause and effect", "MS-ESS2-1/2", "Model how energy drives geologic change.", ("rock cycle", "tectonic energy", "surface processes")),
        ("physical science", "forces and motion", "net force, mass, and changes in motion", "investigation article", "data interpretation", "MS-PS2-1/2", "Use data to relate force, mass, and motion.", ("net force", "mass", "acceleration")),
    ],
    8: [
        ("physical science", "waves", "wave properties and information transfer", "model-and-data article", "model and evidence", "MS-PS4-1/2/3", "Use models to explain wave behavior and communication.", ("amplitude", "frequency", "digital signals")),
        ("space science", "Earth in space", "gravity, orbital motion, and scale in the solar system", "model-based article", "systems reasoning", "MS-ESS1-2/3", "Use models and scale data to explain orbital systems.", ("gravity", "orbits", "scale")),
        ("life science", "natural selection", "variation, selection, and changes in populations", "data-based article", "claim evidence reasoning", "MS-LS4-4/6", "Use evidence to explain natural selection over generations.", ("variation", "selection pressure", "population change")),
        ("physical science", "energy and forces", "kinetic energy, potential energy, and collisions", "investigation article", "data interpretation", "MS-PS3-1/2", "Analyze how mass, speed, and position affect energy.", ("kinetic energy", "potential energy", "energy transfer")),
        ("engineering", "design optimization", "criteria, constraints, testing, and iterative improvement", "engineering case study", "argument from evidence", "MS-ETS1-1/2/3/4", "Compare design solutions using test evidence.", ("criteria", "constraints", "trade-offs")),
    ],
}

CONCEPT_TEMPLATES = [
    "{subtopic}: causes, mechanisms, and consequences",
    "{subtopic}: evidence and interpretation",
    "{subtopic}: chronology and change over time",
    "{subtopic}: comparison of two connected cases",
    "{subtopic}: a common misconception tested against evidence",
    "{subtopic}: a focused real-world case study",
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

    if not isinstance(passage, dict):
        return ["passage must be an object"]
    if not isinstance(questions, list):
        return ["questions must be a list"]
    if not isinstance(vocabulary, list):
        return ["vocabulary must be a list"]
    if any(not isinstance(item, dict) for item in questions):
        return ["every question must be an object"]
    if any(not isinstance(item, dict) for item in vocabulary):
        return ["every vocabulary entry must be an object"]

    if not passage.get("title") or not passage.get("text"):
        errors.append("missing passage title/text")
    if len(vocabulary) != 8:
        errors.append("expected 8 vocabulary words")
    if len(questions) != 8:
        errors.append("expected 8 questions")

    grade = plan.slot.grade
    actual_words = len(_tokens(passage.get("text", "")))
    if grade <= 6 and not 450 <= actual_words <= 650:
        errors.append(f"passage word count out of grade 5-6 range: {actual_words}")
    if grade >= 7 and not 650 <= actual_words <= 850:
        errors.append(f"passage word count out of grade 7-8 range: {actual_words}")

    passage_text = passage.get("text", "")
    for item in vocabulary:
        word = (item.get("word") or "").strip()
        if not word or not _contains_term(passage_text, word):
            errors.append(f"vocabulary word not used in passage: {word or '<missing>'}")

    question_ids = [item.get("id") for item in questions if isinstance(item, dict)]
    if len(question_ids) != len(set(question_ids)):
        errors.append("question ids must be unique")
    for item in questions:
        if not item.get("question") or not item.get("answer"):
            errors.append(f"question {item.get('id', '<missing>')} needs a question and answer")
        if (item.get("type") or "").lower() == "vocabulary_context":
            target_word = (item.get("target_word") or "").strip()
            if not target_word or not _contains_term(passage_text, target_word):
                errors.append(f"vocabulary question target is not in passage: {target_word or '<missing>'}")

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
    slot_map = SCIENCE_SLOTS_BY_GRADE if scope == SCIENCE_READING else HISTORY_SLOTS_BY_GRADE
    slots = slot_map.get(grade, slot_map[6])
    idx = date.fromisoformat(date_str).toordinal() % len(slots)
    domain, topic, subtopic, text_type, skill, standard, learning_goal, required_content = slots[idx]
    return ReadingSlot(grade=grade, domain=domain, topic=topic,
                       subtopic=subtopic, text_type=text_type, skill=skill,
                       standard=standard, learning_goal=learning_goal,
                       required_content=required_content)


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


def _contains_term(text: str, term: str) -> bool:
    normalized_text = " ".join(_tokens(text))
    normalized_term = " ".join(_tokens(term))
    return bool(normalized_term and re.search(rf"\b{re.escape(normalized_term)}\b", normalized_text))


def _external_passage_id(scope: TaskScope, date_str: str, grade: int, concept: str) -> str:
    digest = hashlib.sha256(f"{scope.key}|{date_str}|{grade}|{concept}".encode()).hexdigest()[:12]
    return f"{scope.subject}-{scope.task_type}-{date_str}-{digest}"
