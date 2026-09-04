from dataclasses import dataclass

DEFAULT_DIFFICULTY = "standard"
DIFFICULTY_ORDER = ["guided", "standard", "advanced", "challenge"]


@dataclass(frozen=True)
class DifficultyProfile:
    id: str
    label: str
    prompt: str


_PROFILES = {
    "guided": DifficultyProfile(
        id="guided",
        label="Guided",
        prompt=(
            "Use smaller numbers, direct contexts, and mostly 1-step or clear "
            "2-step questions. Include scaffolding, hints, and worked-example "
            "alignment. Avoid tricky multi-constraint puzzles."
        ),
    ),
    "standard": DifficultyProfile(
        id="standard",
        label="Standard",
        prompt=(
            "Use grade-level numbers and contexts. Use a balanced mix of "
            "1-step and 2-step questions, with a few moderate multi-step items. "
            "Avoid making every problem a challenge problem."
        ),
    ),
    "advanced": DifficultyProfile(
        id="advanced",
        label="Advanced",
        prompt=(
            "Use upper-grade-level complexity, multi-step reasoning, subtle "
            "error analysis, and less scaffolding. Keep problems solvable "
            "without excessive puzzle wording."
        ),
    ),
    "challenge": DifficultyProfile(
        id="challenge",
        label="Challenge",
        prompt=(
            "Keep the existing Part 1, Part 2, and Part 3 formats and required item "
            "counts, but use the demanding end of the requested grade-level standard. "
            "Increase number complexity and combine prerequisite skills where appropriate. "
            "Part 2 must emphasize multi-step transfer, error analysis, comparing methods, "
            "missing values, and justification instead of direct substitution. Part 3 must "
            "require planning across at least three linked conditions or operations. Do not "
            "move to a later grade's curriculum merely to make the work harder."
        ),
    ),
}


def get_difficulty_profile(difficulty: str | None) -> DifficultyProfile:
    key = (difficulty or DEFAULT_DIFFICULTY).strip().lower()
    return _PROFILES.get(key, _PROFILES[DEFAULT_DIFFICULTY])


def list_difficulty_profiles() -> list[DifficultyProfile]:
    return [_PROFILES[key] for key in DIFFICULTY_ORDER]
