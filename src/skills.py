import re
from rapidfuzz import fuzz

def find_evidence(text: str, phrases: list[str]) -> str | None:
    """Return a short snippet around the first occurrence of any phrase."""
    t = text.lower()
    for p in phrases:
        p_l = p.lower()
        idx = t.find(p_l)
        if idx != -1:
            start = max(0, idx - 60)
            end = min(len(text), idx + len(p) + 60)
            return "..." + text[start:end].strip() + "..."
    return None

def detect_skills(text: str, skill_map: dict, fuzzy_threshold: int = 88) -> dict:
    """
    Detect skills in text using:
    1) exact word-boundary matching for aliases
    2) light fuzzy fallback

    skill_map = {skill_name: [aliases...]}
    returns: dict(skill -> {status: 'detected'|'likely', alias: str, evidence: str|None})
    """
    detected: dict = {}
    t = text.lower()

    for skill, aliases in skill_map.items():
        # exact boundary match
        for a in aliases:
            pat = r"\b" + re.escape(a.lower()) + r"\b"
            if re.search(pat, t):
                detected[skill] = {
                    "status": "detected",
                    "alias": a,
                    "evidence": find_evidence(text, aliases)
                }
                break

        if skill in detected:
            continue

        # fuzzy fallback (keep light)
        for a in aliases:
            if len(a) >= 4 and fuzz.partial_ratio(a.lower(), t) >= fuzzy_threshold:
                detected[skill] = {
                    "status": "likely",
                    "alias": a,
                    "evidence": find_evidence(text, aliases)
                }
                break

    return detected
