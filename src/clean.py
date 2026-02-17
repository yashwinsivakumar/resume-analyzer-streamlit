import re

def clean_text(t: str) -> str:
    """Normalize whitespace and remove problematic null characters."""
    t = (t or "").replace("\x00", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t
