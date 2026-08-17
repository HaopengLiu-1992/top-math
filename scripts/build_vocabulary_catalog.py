"""Build the checked-in Grade 5-8 vocabulary catalog.

The app does not need the build-time packages. They are kept in
requirements-vocabulary-build.txt so the catalog can be regenerated with
documented, local sources.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from nltk.corpus import wordnet as wn
from wordfreq import get_frequency_dict, zipf_frequency


ROOT = Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / "config/vocabulary/academic_word_bank_10000.json"
INDEX_PATH = ROOT / "config/vocabulary/vocabulary_index.json"
CURATED_PATH = ROOT / "config/vocabulary/math_science_words.json"

WORD_RE = re.compile(r"^[a-z]{3,18}$")

# Function words and very common grammatical words are useful in passages but
# are poor daily vocabulary targets. Domain and academic overrides can still
# bring a word back when it is important for school reading.
FUNCTION_WORDS = set(
    """
    a an and are as at be been being but by can could did do does doing for from
    had has have having he her here hers herself him himself his how i if in
    into is it its itself me more most my myself no nor not of off on once one
    only or our ours ourselves out over own same she should so some such than
    that the their theirs them themselves then there these they this those to
    too under until up us very was we were what when where which while who whom
    whose why will with would you your yours yourself yourselves
    """.split()
)

ACADEMIC_VERBS = set(
    """
    analyze assess assume calculate classify compare conclude contrast define
    demonstrate describe determine evaluate explain infer identify interpret
    justify organize predict represent summarize support solve apply cite
    clarify communicate construct derive discuss distinguish estimate examine
    formulate illustrate indicate investigate measure observe reason revise
    select synthesize verify
    """.split()
)

# These are high-value Tier 2 words that are often too frequent to survive the
# common-word cutoff below. They are included deliberately for school reading.
ACADEMIC_PRIORITY_WORDS = set(
    """
    although therefore however moreover similarly whereas despite consequently
    evidence source claim context concept process pattern relationship cause
    effect factor method strategy structure function significant specific
    accurate precise valid reliable require involve occur indicate result
    issue approach feature purpose example detail sequence category compare
    contrast infer justify analyze evaluate explain determine identify describe
    summarize interpret predict support conclude argument reason response
    paragraph passage author inferential central relevant complex indicate
    variable constant equation expression proportion percent ratio data graph
    experiment hypothesis observation procedure conclusion model system matter
    energy force motion cell organism species habitat ecosystem adaptation
    climate erosion weathering resource environment population sample outcome
    distribution percent average range probability
    """.split()
)

SCIENCE_PROCESS_WORDS = set(
    """
    hypothesis experiment investigate control procedure result claim reasoning
    accurate precise record trial observation conclusion variable evidence
    model system process pattern cause effect source valid reliable
    """.split()
)

EARTH_WORDS = set(
    """
    rock mineral sediment fossil soil landform plate earthquake volcano
    atmosphere ocean current tide evaporation condensation precipitation runoff
    groundwater renewable nonrenewable resource climate weathering erosion
    """.split()
)

LIFE_WORDS = set(
    """
    organism species community cell tissue organ function structure trait
    inherit genetic reproduce survive consumer producer decomposer predator prey
    ecosystem habitat adaptation photosynthesis respiration competition population
    """.split()
)

PHYSICAL_WORDS = set(
    """
    matter mass weight density particle atom molecule element compound mixture
    solid liquid gas temperature thermal conductor insulator magnet electricity
    circuit friction gravity speed velocity acceleration force motion energy
    """.split()
)

MATH_WORDS = set(
    """
    addition subtraction multiplication division operation calculate compute
    total equal unequal value expression equation solution variable constant
    coefficient term factor multiple integer fraction decimal numerator
    denominator ratio proportion percent percentage reciprocal convert round
    angle degree segment parallel perpendicular vertex polygon triangle
    quadrilateral rectangle square circle radius diameter circumference
    coordinate axis plane base face edge perimeter area volume mean median mode
    table graph chart plot frequency survey sample population probability
    outcome random trend maximum minimum algebra geometry theorem proof slope
    intercept polynomial quadratic linear exponent formula estimate
    """.split()
)

PROPER_NAME_EXCLUSIONS = {
    "america",
    "americas",
    "christ",
    "george",
    "jesus",
    "salem",
    "usa",
    "winslow",
}

PHRASE_DEFINITIONS = {
    "absolute value": "the distance of a number from zero on a number line",
    "bar graph": "a graph that uses bars to compare amounts",
    "dependent variable": "the variable measured in an experiment",
    "food chain": "a sequence showing how energy passes from one organism to another",
    "food web": "a set of connected food chains in an ecosystem",
    "independent variable": "the variable that is changed in an experiment",
    "line plot": "a graph that uses marks above a number line to show data",
    "place value": "the value of a digit based on its position in a number",
    "rational number": "a number that can be written as a ratio of two integers",
    "scatter plot": "a graph that shows how two sets of data are related",
    "surface area": "the total area of all the surfaces of a solid",
    "water cycle": "the continuous movement of water through Earth and its atmosphere",
    "decomposer": "an organism that breaks down dead material and returns nutrients to the ecosystem",
    "groundwater": "water stored below the ground in soil or rock",
    "landform": "a natural feature of Earth's surface, such as a hill or valley",
    "per": "for each unit or group",
}

CATEGORY_ORDER = [
    "math_operations",
    "word_problem_signals",
    "fractions_decimals",
    "geometry_measurement",
    "data_statistics",
    "academic_verbs",
    "science_process",
    "life_science",
    "physical_science",
    "earth_science",
    "math",
    "science",
    "general_academic",
]

DAILY_CATEGORY_PLAN = [
    "math_operations",
    "word_problem_signals",
    "fractions_decimals",
    "geometry_measurement",
    "data_statistics",
    "academic_verbs",
    "science_process",
    "life_science",
    "physical_science",
    "earth_science",
    "general_academic",
]


def _load_curated() -> list[dict]:
    entries = json.loads(CURATED_PATH.read_text())
    return [dict(item, source="curated_math_science_core") for item in entries]


def _definition(word: str, category: str, existing: str = "") -> tuple[str, str]:
    if existing:
        return existing, "curated_local"
    if word in PHRASE_DEFINITIONS:
        return PHRASE_DEFINITIONS[word], "curated_local"

    synsets = wn.synsets(word)
    if not synsets:
        return "a school word used to explain an idea or process", "catalog_fallback"

    def score(synset) -> tuple[int, int, str]:
        lexname = synset.lexname()
        score_value = max((lemma.count() for lemma in synset.lemmas()), default=0)
        if synset.pos() == "v" and category == "academic_verbs":
            score_value += 1000
        if category == "life_science" and lexname in {
            "noun.animal", "noun.biological_process", "noun.body", "noun.food", "noun.plant"
        }:
            score_value += 1000
        if category == "physical_science" and lexname in {
            "noun.phenomenon", "noun.substance", "noun.quantity"
        }:
            score_value += 1000
        if category == "earth_science" and lexname in {"noun.phenomenon", "noun.substance"}:
            score_value += 1000
        if category in {"math", "math_operations", "fractions_decimals", "data_statistics"}:
            if lexname in {"noun.quantity", "noun.cognition", "noun.attribute", "noun.relation"}:
                score_value += 1000
        return score_value, len(synset.definition()), synset.name()

    selected = max(synsets, key=score)
    definition = selected.definition()
    definition = re.split(r"\s*;\s*;?\s*-\s*[A-Z]", definition, maxsplit=1)[0]
    definition = re.sub(r"\s*;\s*;\s*-\s*[^;]+$", "", definition)
    definition = re.sub(r";\s+[A-Z][^;]*$", "", definition)
    definition = re.sub(r"(?:;\s*){2,}", "; ", definition)
    definition = re.sub(r";\s*$", "", definition)
    definition = re.sub(r"\s*;\s*-\s*[^;]+$", "", definition)
    definition = re.sub(r"\s+", " ", definition).strip()
    return definition, "wordnet_3.0"


def _category(word: str, old_item: dict | None, synsets: list) -> str:
    old_category = (old_item or {}).get("category")
    if old_category in CATEGORY_ORDER:
        return old_category
    if word in ACADEMIC_VERBS:
        return "academic_verbs"
    if word in SCIENCE_PROCESS_WORDS:
        return "science_process"
    if word in MATH_WORDS:
        return "math"
    if word in EARTH_WORDS:
        return "earth_science"
    if word in LIFE_WORDS:
        return "life_science"
    if word in PHYSICAL_WORDS:
        return "physical_science"
    return "general_academic"


def _minimum_grade(zipf: float, category: str, priority: bool) -> int:
    if zipf >= 4.2:
        minimum = 5
    elif zipf >= 3.9:
        minimum = 6
    elif zipf >= 3.6:
        minimum = 7
    else:
        minimum = 8
    if priority or category in {
        "math", "science", "science_process", "life_science", "physical_science", "earth_science"
    }:
        minimum = max(5, minimum - 1)
    return minimum


def _stage_for_grade(minimum_grade: int) -> str:
    if minimum_grade <= 5:
        return "cn_middle_school"
    if minimum_grade <= 7:
        return "cn_high_school"
    return "cn_high_school_extension"


def _band_for_grade(minimum_grade: int) -> str:
    return f"us_grade_{minimum_grade}_8"


def _catalog_item(
    word: str,
    old_item: dict | None,
    rank: int | None,
    zipf: float,
    priority_band: int,
) -> dict:
    old_item = old_item or {}
    category = _category(word, old_item, wn.synsets(word))
    is_curated = old_item.get("source") == "curated_math_science_core"
    if is_curated:
        minimum_grade = 5
        maximum_grade = 8
        source = "curated_math_science_core"
        grade_basis = "curated_math_science_core"
    else:
        minimum_grade = _minimum_grade(zipf, category, priority_band <= 2)
        maximum_grade = 8
        source = "wordfreq_3.1.1"
        grade_basis = "frequency_band_with_domain_overlay"

    existing_definition = old_item.get("definition", "") if is_curated else ""
    definition, definition_source = _definition(word, category, existing_definition)
    return {
        "word": word,
        "category": category,
        "chinese": old_item.get("chinese", ""),
        "definition": definition,
        "cn_stage": _stage_for_grade(minimum_grade),
        "us_band": _band_for_grade(minimum_grade),
        "grade_min": minimum_grade,
        "grade_max": maximum_grade,
        "grade_basis": grade_basis,
        "frequency_rank": rank,
        "zipf_frequency": round(zipf, 2),
        "source": source,
        "definition_source": definition_source,
        "learning_priority": priority_band,
    }


def build() -> tuple[list[dict], dict]:
    curated = _load_curated()
    if len(curated) != 275:
        raise RuntimeError(f"expected 275 curated entries, found {len(curated)}")

    frequencies = get_frequency_dict("en", wordlist="best")
    ranked_words = sorted(
        frequencies,
        key=lambda word: (-zipf_frequency(word, "en"), word),
    )
    ranked = {word: index for index, word in enumerate(ranked_words, start=1)}
    valid: dict[str, tuple[int, float, list]] = {}
    for word in ranked_words:
        if (
            not WORD_RE.fullmatch(word)
            or word in FUNCTION_WORDS
            or word in PROPER_NAME_EXCLUSIONS
        ):
            continue
        frequency = zipf_frequency(word, "en")
        if frequency < 3.0:
            continue
        synsets = wn.synsets(word)
        if not synsets:
            continue
        valid[word] = (ranked[word], frequency, synsets)

    domain_words: set[str] = set()
    priority_words = (ACADEMIC_PRIORITY_WORDS | MATH_WORDS) & valid.keys()
    selected: list[dict] = []
    selected_words: set[str] = set()

    for item in curated:
        word = item["word"]
        rank, frequency, _ = valid.get(word, (None, 0.0, []))
        selected.append(_catalog_item(word, item, rank, frequency, 0))
        selected_words.add(word)

    def add_words(words: list[str], priority_band: int) -> None:
        for word in words:
            if len(selected) >= 10000 or word in selected_words:
                continue
            rank, frequency, _ = valid[word]
            selected.append(
                _catalog_item(word, None, rank, frequency, priority_band)
            )
            selected_words.add(word)

    add_words(
        sorted(domain_words, key=lambda word: (-valid[word][1], word)),
        1,
    )
    add_words(
        sorted(priority_words, key=lambda word: (-valid[word][1], word)),
        2,
    )
    general_words = sorted(
        (word for word in valid if valid[word][1] < 5.3 and word not in selected_words),
        key=lambda word: (-valid[word][1], word),
    )
    low_frequency_words = [word for word in general_words if valid[word][1] < 3.6]
    mid_frequency_words = [word for word in general_words if valid[word][1] >= 3.6]
    low_frequency_target = min(500, len(low_frequency_words))
    mid_target = max(0, 10000 - len(selected) - low_frequency_target)
    add_words(mid_frequency_words[:mid_target], 3)
    add_words(low_frequency_words, 4)
    add_words(mid_frequency_words, 3)
    if len(selected) < 10000:
        add_words(
            sorted(valid, key=lambda word: (-valid[word][1], word)),
            4,
        )
    if len(selected) != 10000:
        raise RuntimeError(f"could only build {len(selected)} entries")

    by_stage_category: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for item in selected:
        by_stage_category[item["cn_stage"]][item["category"]].append(item["word"])

    index = {
        "version": 3,
        "catalog_version": "g5-g8-2026.08",
        "description": (
            "Grade-aware local vocabulary catalog. The runtime selects a small daily set "
            "and never sends this catalog to the model."
        ),
        "grade_levels": [5, 6, 7, 8],
        "stage_order": ["cn_middle_school", "cn_high_school", "cn_high_school_extension"],
        "category_order": CATEGORY_ORDER,
        "daily_category_plan": DAILY_CATEGORY_PLAN,
        "learning_sequence": [item["word"] for item in selected],
        "curated_count": len(curated),
        "catalog_count": len(selected),
        "sources": [
            "wordfreq 3.1.1 frequency data",
            "Princeton WordNet 3.0 definitions",
            "curated_math_science_core local teaching set",
        ],
        "by_stage_category": {
            stage: {category: words for category, words in categories.items()}
            for stage, categories in by_stage_category.items()
        },
    }
    return selected, index


def main() -> None:
    bank, index = build()
    BANK_PATH.write_text(json.dumps(bank, indent=2, ensure_ascii=False) + "\n")
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    fallback_count = sum(item["definition_source"] == "catalog_fallback" for item in bank)
    categories = defaultdict(int)
    for item in bank:
        categories[item["category"]] += 1
    print(f"wrote {len(bank)} words to {BANK_PATH}")
    print(f"curated={index['curated_count']} fallback_definitions={fallback_count}")
    print("categories=" + json.dumps(dict(sorted(categories.items())), sort_keys=True))


if __name__ == "__main__":
    main()
