import hashlib
import re

_MD5_RE = re.compile(r'^[0-9a-f]{32}$')


def fingerprint_hash(fingerprint: str) -> str:
    return hashlib.md5(fingerprint.strip().lower().encode()).hexdigest()


def _normalize(fp: str) -> str:
    return fp.strip().lower()


def extract_all_fingerprints(homework: dict) -> list[str]:
    """Extract raw (normalized) fingerprint strings from homework."""
    fps = []
    for part in homework.get("parts", {}).values():
        for q in part:
            fp = q.get("fingerprint", "")
            if fp:
                fps.append(_normalize(fp))
    challenge = homework.get("weekly_challenge")
    if challenge and "fingerprint" in challenge:
        fps.append(_normalize(challenge["fingerprint"]))
    return fps


def check_duplicates(homework: dict, forbidden: set) -> list[str]:
    """
    Check for duplicate questions.
    forbidden may contain raw fingerprint strings (new) or MD5 hashes (legacy).
    Returns list of raw fingerprint strings that are duplicates.
    """
    forbidden_raw = {f for f in forbidden if not _MD5_RE.match(f)}
    forbidden_hashes = {f for f in forbidden if _MD5_RE.match(f)}

    duplicates = []
    seen: set[str] = set()

    for part in homework.get("parts", {}).values():
        for q in part:
            fp = q.get("fingerprint", "")
            if not fp:
                continue
            normalized = _normalize(fp)
            h = fingerprint_hash(fp)

            if normalized in forbidden_raw or h in forbidden_hashes or normalized in seen:
                duplicates.append(normalized)
            seen.add(normalized)

    return duplicates
