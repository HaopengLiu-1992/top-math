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
            "Use rich, non-routine problems that require planning, justification, "
            "or connecting multiple skills. Keep the worksheet shorter if needed "
            "but make the reasoning deeper."
        ),
    ),
}


def get_difficulty_profile(difficulty: str | None) -> DifficultyProfile:
    key = (difficulty or DEFAULT_DIFFICULTY).strip().lower()
    return _PROFILES.get(key, _PROFILES[DEFAULT_DIFFICULTY])


def list_difficulty_profiles() -> list[DifficultyProfile]:
    return [_PROFILES[key] for key in DIFFICULTY_ORDER]
