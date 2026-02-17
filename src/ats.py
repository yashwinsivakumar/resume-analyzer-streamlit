import re

def basic_ats_checks(resume_text: str) -> list[str]:
    """Simple, lightweight heuristics to mimic common ATS parsing issues."""
    warns: list[str] = []

    if len(resume_text) < 800:
        warns.append("Resume text looks short — the PDF might be scanned or extraction may have failed.")

    if not re.search(r"\b(linkedin|github)\b", resume_text.lower()):
        warns.append("Consider adding LinkedIn/GitHub links if you have them.")

    bullets = resume_text.count("•") + resume_text.count("- ")
    if bullets < 5:
        warns.append("Add more bullet points to show impact and responsibilities.")

    if not re.search(r"\bemail\b", resume_text.lower()) and "@" not in resume_text:
        warns.append("Ensure your email is visible and ATS-readable.")

    return warns
