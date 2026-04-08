import hashlib


def fingerprint_hash(fingerprint: str) -> str:
    return hashlib.md5(fingerprint.strip().lower().encode()).hexdigest()



def extract_all_fingerprints(homework: dict) -> list[str]:
    hashes = []
    for part in homework.get("parts", {}).values():
        for q in part:
            if "fingerprint" in q:
                hashes.append(fingerprint_hash(q["fingerprint"]))
    challenge = homework.get("weekly_challenge")
    if challenge and "fingerprint" in challenge:
        hashes.append(fingerprint_hash(challenge["fingerprint"]))
    return hashes


def check_duplicates(homework: dict, forbidden: set) -> list[str]:
    duplicates = []
    seen: set[str] = set()
    for part in homework.get("parts", {}).values():
        for q in part:
            fp = q.get("fingerprint", "")
            if not fp:
                continue  # skip questions missing fingerprint
            h = fingerprint_hash(fp)
            if h in forbidden or h in seen:
                duplicates.append(h)
            seen.add(h)
    return duplicates
