import json
import streamlit as st

from src.extract import extract_any
from src.clean import clean_text
from src.scoring import tfidf_similarity
from src.skills import detect_skills, get_all_skills_from_taxonomy
from src.ats import basic_ats_checks

st.set_page_config(page_title="Resume Analyzer", layout="wide")
st.title("Lightweight Resume Analyzer (Streamlit)")
st.caption("Role-based skill gap detection + TF-IDF similarity + evidence snippets (CPU friendly).")

# Load taxonomy
with open("data/skills_taxonomy.json", "r", encoding="utf-8") as f:
    TAX = json.load(f)

role_keys = list(TAX.keys())
role_key = st.selectbox("Choose target role", role_keys, format_func=lambda k: TAX[k]["title"])

col1, col2 = st.columns(2)
with col1:
    resume_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
with col2:
    jd_text_input = st.text_area("Paste Job Description", height=260, placeholder="Paste the job description here...")

if st.button("Analyze"):
    if not resume_file or not jd_text_input.strip():
        st.error("Upload a resume and paste a job description.")
        st.stop()

    file_bytes = resume_file.read()
    extraction_result = extract_any(resume_file.name, file_bytes)
    
    # Show extraction warnings if any
    if extraction_result.warnings:
        for warn in extraction_result.warnings:
            st.warning(warn)
    
    if not extraction_result.success:
        st.error("Failed to extract text from the resume. Please try a different file.")
        st.stop()
    
    resume_text = extraction_result.text
    jd_text = clean_text(jd_text_input)

    # Similarity score (lightweight)
    sim = tfidf_similarity(resume_text, jd_text)
    match_score = int(round(sim * 100))

    # Skill detection - use helper to convert new taxonomy format to legacy format
    skill_map = get_all_skills_from_taxonomy(TAX[role_key])
    resume_sk = detect_skills(resume_text, skill_map)
    jd_sk = detect_skills(jd_text, skill_map)

    resume_detected = set(resume_sk.keys())
    jd_detected = set(jd_sk.keys())

    matched = sorted(resume_detected & jd_detected)
    missing = sorted(jd_detected - resume_detected)
    extra = sorted(resume_detected - jd_detected)

    # ATS warnings
    warns = basic_ats_checks(resume_text)

    st.subheader("Results")
    a, b, c = st.columns(3)
    a.metric("Match Score (TF-IDF)", f"{match_score}/100")
    b.metric("Matched Skills", str(len(matched)))
    c.metric("Missing Skills", str(len(missing)))

    left, right = st.columns(2)
    with left:
        st.markdown("### ✅ Matched Skills (with evidence)")
        if matched:
            for s in matched:
                info = resume_sk.get(s, {})
                badge = "✅" if info.get("status") == "detected" else "🟡"
                st.write(f"{badge} **{s}** (via: {info.get('alias')})")
                if info.get("evidence"):
                    st.caption(info["evidence"])
        else:
            st.write("No matched skills detected for this role taxonomy.")

        st.markdown("### ➕ Extra Skills (in resume, not in JD)")
        st.write(extra if extra else ["(none)"])

    with right:
        st.markdown("### ⚠️ Missing Skills (in JD, not found in resume)")
        st.write(missing if missing else ["(none)"])

        st.markdown("### 🧾 ATS / Formatting Tips")
        st.write(warns if warns else ["Looks okay 👍"])

    st.markdown("### Practical suggestions")
    if missing:
        st.write(
            "- Only add missing skills if you genuinely have them.\n"
            "- Add 1–2 project bullets that prove those skills (tool + result).\n"
            "- Use JD wording truthfully to help ATS matching."
        )
    else:
        st.write("- Strong alignment. Improve impact by adding metrics (accuracy, % improvement, time saved).")

    with st.expander("Debug: extracted resume text"):
        st.write(resume_text[:5000] + ("..." if len(resume_text) > 5000 else ""))
