from domain.curriculum import CurriculumProvider
from curriculum.math.common_core.provider import MathCommonCoreProvider

_PROVIDERS: dict[str, CurriculumProvider] = {
    "math": MathCommonCoreProvider(),
}


def get_provider(subject: str) -> CurriculumProvider:
    key = subject.strip().lower()
    try:
        return _PROVIDERS[key]
    except KeyError as exc:
        available = ", ".join(sorted(_PROVIDERS))
        raise ValueError(f"Unsupported subject {subject!r}. Available: {available}") from exc


def list_providers() -> list[CurriculumProvider]:
    return list(_PROVIDERS.values())
