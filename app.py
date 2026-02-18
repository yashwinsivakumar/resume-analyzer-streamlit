"""
Resume Intelligence System - Professional UI

A comprehensive resume analysis platform featuring:
- Multi-dimensional hybrid scoring
- Section-aware skill detection  
- Semantic similarity analysis
- ATS compatibility checking
- Impact analysis
- Role recommendations
- Exportable reports
"""

import json
import streamlit as st

# Import all modules
from src.extract import extract_any
from src.clean import clean_text
from src.sections import parse_resume, SectionType
from src.skills import analyze_skills_sectioned, get_all_skills_from_taxonomy
from src.hybrid_scoring import compute_hybrid_score, HybridScore
from src.semantic import semantic_similarity, smart_similarity
from src.ats import analyze_ats, ATSAnalysis
from src.impact import analyze_impact, ImpactAnalysis
from src.recommendations import recommend_roles, RoleRecommendation
from src.report import ReportData, generate_markdown_report, generate_html_report, generate_json_report

# Page Configuration
st.set_page_config(
    page_title="Resume Intelligence System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e40af;
        text-align: center;
        padding: 1rem 0;
    }
    .score-card {
        background: linear-gradient(135deg, #2563eb, #1e40af);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .score-value {
        font-size: 3.5rem;
        font-weight: bold;
    }
    .score-label {
        font-size: 1.2rem;
        opacity: 0.9;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2563eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .skill-tag-matched {
        background: #10b981;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.85rem;
    }
    .skill-tag-missing {
        background: #ef4444;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.85rem;
    }
    .skill-tag-bonus {
        background: #3b82f6;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.85rem;
    }
    .recommendation-item {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
        color: #1f2937;
    }
    .ats-pass { color: #10b981; }
    .ats-warning { color: #f59e0b; }
    .ats-fail { color: #ef4444; }
</style>
""", unsafe_allow_html=True)


# Load Taxonomy
@st.cache_data
def load_taxonomy():
    with open("data/skills_taxonomy.json", "r", encoding="utf-8") as f:
        return json.load(f)


TAX = load_taxonomy()

# Header
st.markdown('<h1 class="main-header">📄 Resume Intelligence System</h1>', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align: center; color: #6b7280;">Professional resume analysis with AI-powered insights</p>',
    unsafe_allow_html=True
)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    role_keys = list(TAX.keys())
    selected_role = st.selectbox(
        "Target Role",
        role_keys,
        format_func=lambda k: TAX[k]["title"]
    )
    
    st.divider()
    
    st.subheader("Analysis Options")
    enable_semantic = st.checkbox("Semantic Analysis", value=True, help="Use AI embeddings for meaning-based matching")
    enable_role_rec = st.checkbox("Role Recommendations", value=True, help="Analyze fit across all roles")
    
    st.divider()
    
    st.markdown("### 📊 Score Weights")
    st.caption("Final Score = 40% Skills + 30% Semantic + 20% Evidence + 10% Impact")

# Main Input Section
col1, col2 = st.columns(2)

with col1:
    st.subheader("📎 Upload Resume")
    resume_file = st.file_uploader(
        "PDF, DOCX, or TXT",
        type=["pdf", "docx", "txt"],
        label_visibility="collapsed"
    )

with col2:
    st.subheader("📋 Job Description")
    jd_text_input = st.text_area(
        "Paste the job description",
        height=200,
        placeholder="Paste the job description here to analyze skill alignment...",
        label_visibility="collapsed"
    )

# Analyze Button
analyze_btn = st.button("🔍 Analyze Resume", type="primary", use_container_width=True)

if analyze_btn:
    if not resume_file or not jd_text_input.strip():
        st.error("⚠️ Please upload a resume AND paste a job description.")
        st.stop()
    
    # Show progress
    progress_bar = st.progress(0, text="Extracting text...")
    
    # 1. Extract Text
    file_bytes = resume_file.read()
    extraction_result = extract_any(resume_file.name, file_bytes)
    
    if extraction_result.warnings:
        for warn in extraction_result.warnings:
            st.warning(warn)
    
    if not extraction_result.success:
        st.error("❌ Failed to extract text from the resume. Please try a different file.")
        st.stop()
    
    resume_text = extraction_result.text
    jd_text = clean_text(jd_text_input)
    
    progress_bar.progress(20, text="Parsing sections...")
    
    # 2. Parse Sections
    parsed_resume = parse_resume(resume_text)
    
    progress_bar.progress(40, text="Analyzing skills...")
    
    # 3. Compute Hybrid Score
    role_taxonomy = TAX[selected_role]
    hybrid_score = compute_hybrid_score(resume_text, jd_text, role_taxonomy, parsed_resume)
    
    progress_bar.progress(60, text="Running ATS checks...")
    
    # 4. ATS Analysis
    ats_analysis = analyze_ats(resume_text, parsed_resume, jd_text)
    
    progress_bar.progress(75, text="Analyzing impact...")
    
    # 5. Impact Analysis
    impact_analysis = analyze_impact(resume_text, parsed_resume)
    
    # 6. Role Recommendations (optional)
    role_recommendation = None
    if enable_role_rec:
        progress_bar.progress(90, text="Analyzing role fit...")
        role_recommendation = recommend_roles(resume_text, TAX, parsed_resume)
    
    progress_bar.progress(100, text="Complete!")
    progress_bar.empty()
    
    # Store in session for report generation
    st.session_state['report_data'] = ReportData(
        hybrid_score=hybrid_score,
        ats_analysis=ats_analysis,
        impact_analysis=impact_analysis,
        role_recommendation=role_recommendation,
        job_title=TAX[selected_role]["title"]
    )
    
    # ============ RESULTS DISPLAY ============
    
    st.divider()
    
    # Overall Score Card
    st.markdown(f"""
    <div class="score-card">
        <div class="score-value">{hybrid_score.final_percentage}/100</div>
        <div class="score-label">{hybrid_score.final_level.value}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")
    
    # Score Breakdown
    st.subheader("📊 Score Breakdown")
    
    score_cols = st.columns(4)
    for i, comp in enumerate(hybrid_score.all_components):
        with score_cols[i]:
            st.metric(
                label=comp.name,
                value=f"{comp.percentage}%",
                delta=f"{int(comp.weight*100)}% weight",
                help=comp.details
            )
    
    st.divider()
    
    # Two Column Layout for Details
    left_col, right_col = st.columns(2)
    
    with left_col:
        # Skill Analysis
        st.subheader("🎯 Skill Analysis")
        
        if hybrid_score.skill_analysis:
            skill_analysis = hybrid_score.skill_analysis
            
            # Must-Have Skills
            st.markdown("**Must-Have Skills**")
            if skill_analysis.must_have_matched:
                matched_html = " ".join([
                    f'<span class="skill-tag-matched">✓ {s.replace("_", " ").title()}</span>'
                    for s in skill_analysis.must_have_matched
                ])
                st.markdown(matched_html, unsafe_allow_html=True)
            
            if skill_analysis.must_have_missing:
                missing_html = " ".join([
                    f'<span class="skill-tag-missing">✗ {s.replace("_", " ").title()}</span>'
                    for s in skill_analysis.must_have_missing
                ])
                st.markdown(missing_html, unsafe_allow_html=True)
            
            st.markdown("")
            
            # Nice-to-Have Skills
            st.markdown("**Nice-to-Have Skills**")
            if skill_analysis.nice_to_have_matched:
                bonus_html = " ".join([
                    f'<span class="skill-tag-bonus">✓ {s.replace("_", " ").title()}</span>'
                    for s in skill_analysis.nice_to_have_matched
                ])
                st.markdown(bonus_html, unsafe_allow_html=True)
            
            # Coverage metrics
            st.markdown("")
            st.markdown(f"""
            | Metric | Value |
            |--------|-------|
            | Must-Have Coverage | {int(skill_analysis.must_have_coverage * 100)}% |
            | Nice-to-Have Coverage | {int(skill_analysis.nice_to_have_coverage * 100)}% |
            | Skills Proven (not just listed) | {int(skill_analysis.proven_skills_ratio * 100)}% |
            """)
        
        st.divider()
        
        # Impact Analysis
        st.subheader("💪 Impact Analysis")
        
        impact_cols = st.columns(3)
        with impact_cols[0]:
            st.metric("Strong Verbs", impact_analysis.total_strong_verbs)
        with impact_cols[1]:
            st.metric("Weak Phrases", impact_analysis.total_weak_verbs, delta_color="inverse")
        with impact_cols[2]:
            st.metric("Metrics Found", impact_analysis.total_metrics)
        
        if impact_analysis.weak_verbs:
            st.markdown("**Phrases to Improve:**")
            seen = set()
            for verb in impact_analysis.weak_verbs[:3]:
                if verb.verb not in seen:
                    seen.add(verb.verb)
                    st.markdown(f'- "{verb.verb}" → {verb.suggestion}')
    
    with right_col:
        # ATS Analysis
        st.subheader("🤖 ATS Compatibility")
        
        ats_score_col, ats_detail_col = st.columns([1, 2])
        with ats_score_col:
            st.metric("ATS Score", f"{ats_analysis.ats_percentage}%")
        with ats_detail_col:
            st.markdown(f"""
            ✅ Passed: {ats_analysis.passed_checks} | 
            ⚠️ Warnings: {ats_analysis.warning_checks} | 
            ❌ Failed: {ats_analysis.failed_checks}
            """)
        
        # Show ATS Checks
        with st.expander("View All ATS Checks", expanded=False):
            for check in ats_analysis.checks:
                status_class = {
                    "pass": "ats-pass",
                    "warning": "ats-warning", 
                    "fail": "ats-fail"
                }.get(check.status.value, "")
                
                st.markdown(f"""
                <span class="{status_class}">{check.icon}</span> **{check.name}**: {check.message}
                """, unsafe_allow_html=True)
                if check.suggestion:
                    st.caption(f"  💡 {check.suggestion}")
        
        # Contact Info
        st.markdown("**Detected Contact Info:**")
        contact = ats_analysis.contact_info
        contact_items = []
        if contact.email:
            contact_items.append(f"📧 {contact.email}")
        if contact.phone:
            contact_items.append(f"📱 {contact.phone}")
        if contact.linkedin:
            contact_items.append(f"🔗 LinkedIn")
        if contact.github:
            contact_items.append(f"💻 GitHub")
        
        st.markdown(" | ".join(contact_items) if contact_items else "No contact info detected")
        
        st.divider()
        
        # Role Recommendations
        if role_recommendation:
            st.subheader("🎭 Role Fit Analysis")
            
            for match in role_recommendation.top_matches:
                # Color code based on fit
                if match.alignment_score >= 0.6:
                    bar_color = "green"
                elif match.alignment_score >= 0.4:
                    bar_color = "orange"
                else:
                    bar_color = "red"
                
                st.markdown(f"**{match.role_title}** - {match.fit_level}")
                st.progress(match.alignment_score, text=f"{match.alignment_percentage}%")
    
    st.divider()
    
    # Recommendations Section
    st.subheader("💡 Top Recommendations")
    
    rec_cols = st.columns(2)
    suggestions = hybrid_score.top_suggestions[:6]
    
    for i, sug in enumerate(suggestions):
        with rec_cols[i % 2]:
            st.markdown(f"""
            <div class="recommendation-item">
                <strong>{i+1}.</strong> {sug}
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # Export Section
    st.subheader("📥 Export Report")
    
    export_cols = st.columns(4)
    
    report_data = st.session_state.get('report_data')
    
    if report_data:
        with export_cols[0]:
            md_report = generate_markdown_report(report_data)
            st.download_button(
                "📄 Markdown",
                md_report,
                file_name="resume_report.md",
                mime="text/markdown"
            )
        
        with export_cols[1]:
            html_report = generate_html_report(report_data)
            st.download_button(
                "🌐 HTML",
                html_report,
                file_name="resume_report.html",
                mime="text/html"
            )
        
        with export_cols[2]:
            json_report = generate_json_report(report_data)
            st.download_button(
                "📊 JSON",
                json_report,
                file_name="resume_report.json",
                mime="application/json"
            )
        
        with export_cols[3]:
            st.download_button(
                "📋 Text",
                md_report,  # Using markdown as text
                file_name="resume_report.txt",
                mime="text/plain"
            )
    
    # Debug Section
    with st.expander("🔧 Debug: View Extracted Text"):
        st.text_area(
            "Resume Text",
            resume_text[:5000] + ("..." if len(resume_text) > 5000 else ""),
            height=200,
            disabled=True
        )
        
        st.markdown("**Detected Sections:**")
        for section in parsed_resume.sections:
            st.markdown(f"- {section.section_type.value}: {section.word_count} words")

# Footer
st.divider()
st.markdown(
    '<p style="text-align: center; color: #9ca3af; font-size: 0.85rem;">'
    'Resume Intelligence System | Built with Streamlit | CPU-Friendly Analysis'
    '</p>',
    unsafe_allow_html=True
)
