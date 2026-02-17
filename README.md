# Resume Analyzer (Streamlit)

A lightweight, CPU-friendly resume analyzer that compares a resume with a job description and reports:
- TF-IDF similarity score (0–100)
- Role-based matched / missing / extra skills
- Evidence snippets for detected skills
- Basic ATS-style formatting tips

## Features
- Upload resume: PDF / DOCX / TXT
- Paste job description
- Select target role (AI/ML Intern, Data Science Intern, Software Engineer Intern)
- Explainable outputs (evidence snippets)

## Setup
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- Scanned/image-based PDFs may not extract text well.
- Missing skills means **not detected** in the text, not that you don't know it.
- Only add skills you genuinely have and can demonstrate in projects/experience.

## Customize roles/skills
Edit `data/skills_taxonomy.json` to add more roles, skills, and aliases.
