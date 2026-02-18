"""
Report Generator

Generates professional, exportable reports in multiple formats:
- PDF (using reportlab or HTML-to-PDF)
- HTML
- Markdown
- JSON (for API/integration)

Reports include:
- Overall score breakdown
- Matched/missing skills with evidence
- ATS analysis results
- Impact analysis
- Recommendations
"""

import json
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
import io

from .hybrid_scoring import HybridScore
from .skills import SkillAnalysisResult
from .ats import ATSAnalysis
from .impact import ImpactAnalysis
from .recommendations import RoleRecommendation


@dataclass
class ReportData:
    """All data needed for report generation."""
    hybrid_score: HybridScore
    ats_analysis: ATSAnalysis
    impact_analysis: ImpactAnalysis
    role_recommendation: Optional[RoleRecommendation] = None
    job_title: Optional[str] = None
    generated_at: str = ""
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")


def generate_markdown_report(data: ReportData) -> str:
    """Generate a detailed Markdown report."""
    lines = []
    
    # Header
    lines.append("# Resume Analysis Report")
    lines.append(f"*Generated: {data.generated_at}*")
    if data.job_title:
        lines.append(f"*Target Role: {data.job_title}*")
    lines.append("")
    
    # Overall Score
    lines.append("## Overall Score")
    lines.append(f"### {data.hybrid_score.final_percentage}/100 ({data.hybrid_score.final_level.value})")
    lines.append("")
    
    # Score Breakdown
    lines.append("## Score Breakdown")
    lines.append("")
    lines.append("| Component | Score | Weight | Details |")
    lines.append("|-----------|-------|--------|---------|")
    for comp in data.hybrid_score.all_components:
        lines.append(f"| {comp.name} | {comp.percentage}% | {int(comp.weight*100)}% | {comp.details} |")
    lines.append("")
    
    # Skill Analysis
    if data.hybrid_score.skill_analysis:
        skill = data.hybrid_score.skill_analysis
        lines.append("## Skill Analysis")
        lines.append("")
        
        lines.append("### ✅ Matched Must-Have Skills")
        if skill.must_have_matched:
            for s in skill.must_have_matched:
                detected = skill.detected_skills.get(s)
                evidence = ""
                if detected and detected.best_evidence:
                    evidence = f" (found in {detected.best_evidence.section_type.value})"
                lines.append(f"- {s.replace('_', ' ').title()}{evidence}")
        else:
            lines.append("- None matched")
        lines.append("")
        
        lines.append("### ❌ Missing Must-Have Skills")
        if skill.must_have_missing:
            for s in skill.must_have_missing:
                lines.append(f"- {s.replace('_', ' ').title()}")
        else:
            lines.append("- None missing! Great job!")
        lines.append("")
        
        lines.append("### ➕ Matched Nice-to-Have Skills")
        if skill.nice_to_have_matched:
            for s in skill.nice_to_have_matched:
                lines.append(f"- {s.replace('_', ' ').title()}")
        else:
            lines.append("- None matched")
        lines.append("")
    
    # ATS Analysis
    lines.append("## ATS Compatibility")
    lines.append(f"**ATS Score: {data.ats_analysis.ats_percentage}%**")
    lines.append("")
    
    lines.append("### Checks")
    for check in data.ats_analysis.checks:
        lines.append(f"- {check.icon} **{check.name}**: {check.message}")
        if check.suggestion:
            lines.append(f"  - *Suggestion: {check.suggestion}*")
    lines.append("")
    
    # Contact Info
    contact = data.ats_analysis.contact_info
    lines.append("### Detected Contact Info")
    lines.append(f"- Email: {contact.email or 'Not found'}")
    lines.append(f"- Phone: {contact.phone or 'Not found'}")
    lines.append(f"- LinkedIn: {contact.linkedin or 'Not found'}")
    lines.append(f"- GitHub: {contact.github or 'Not found'}")
    lines.append("")
    
    # Impact Analysis
    lines.append("## Impact Analysis")
    lines.append(f"**Impact Score: {int(data.impact_analysis.overall_score * 100)}% ({data.impact_analysis.impact_level})**")
    lines.append("")
    lines.append(f"- Strong action verbs: {data.impact_analysis.total_strong_verbs}")
    lines.append(f"- Weak phrases to fix: {data.impact_analysis.total_weak_verbs}")
    lines.append(f"- Quantified metrics: {data.impact_analysis.total_metrics}")
    lines.append("")
    
    if data.impact_analysis.weak_verbs:
        lines.append("### Phrases to Improve")
        seen = set()
        for verb in data.impact_analysis.weak_verbs[:5]:
            if verb.verb not in seen:
                seen.add(verb.verb)
                lines.append(f"- \"{verb.verb}\" → {verb.suggestion}")
        lines.append("")
    
    # Role Recommendations
    if data.role_recommendation:
        lines.append("## Role Fit Analysis")
        lines.append("")
        for match in data.role_recommendation.top_matches:
            lines.append(f"- **{match.role_title}**: {match.alignment_percentage}% ({match.fit_level})")
        lines.append("")
    
    # Recommendations
    lines.append("## Top Recommendations")
    lines.append("")
    for i, sug in enumerate(data.hybrid_score.top_suggestions[:5], 1):
        lines.append(f"{i}. {sug}")
    
    if data.impact_analysis.suggestions:
        lines.append("")
        lines.append("### Impact Improvements")
        for sug in data.impact_analysis.suggestions[:3]:
            lines.append(f"- {sug}")
    
    lines.append("")
    lines.append("---")
    lines.append("*Report generated by Resume Intelligence System*")
    
    return "\n".join(lines)


def generate_html_report(data: ReportData) -> str:
    """Generate an HTML report with styling."""
    md_content = generate_markdown_report(data)
    
    # Convert basic markdown to HTML
    html_content = md_content
    
    # Headers
    html_content = html_content.replace("# Resume Analysis Report", "<h1>Resume Analysis Report</h1>")
    
    # Simple replacements (for basic rendering)
    import re
    html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
    html_content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_content)
    html_content = re.sub(r'^- (.+)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)
    html_content = html_content.replace('\n\n', '</p><p>')
    
    # Wrap in HTML template
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Analysis Report</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 40px 20px;
                background: #f5f5f5;
                color: #333;
            }}
            h1 {{
                color: #2563eb;
                border-bottom: 3px solid #2563eb;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #1e40af;
                margin-top: 30px;
                border-left: 4px solid #2563eb;
                padding-left: 15px;
            }}
            h3 {{
                color: #374151;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            th, td {{
                border: 1px solid #e5e7eb;
                padding: 12px;
                text-align: left;
            }}
            th {{
                background: #2563eb;
                color: white;
            }}
            tr:nth-child(even) {{
                background: #f9fafb;
            }}
            li {{
                margin: 8px 0;
            }}
            .score-box {{
                background: linear-gradient(135deg, #2563eb, #1e40af);
                color: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                font-size: 48px;
                font-weight: bold;
                margin: 20px 0;
            }}
            .pass {{ color: #10b981; }}
            .warning {{ color: #f59e0b; }}
            .fail {{ color: #ef4444; }}
            em {{
                color: #6b7280;
            }}
        </style>
    </head>
    <body>
        <div class="score-box">
            {data.hybrid_score.final_percentage}/100
            <div style="font-size: 18px; font-weight: normal; margin-top: 10px;">
                {data.hybrid_score.final_level.value}
            </div>
        </div>
        {html_content}
    </body>
    </html>
    """
    
    return html


def generate_json_report(data: ReportData) -> str:
    """Generate a JSON report for API/integration."""
    report = {
        "generated_at": data.generated_at,
        "job_title": data.job_title,
        "scores": {
            "final": data.hybrid_score.final_percentage,
            "level": data.hybrid_score.final_level.value,
            "components": {
                comp.name: {
                    "score": comp.percentage,
                    "weight": int(comp.weight * 100),
                    "details": comp.details
                }
                for comp in data.hybrid_score.all_components
            }
        },
        "skills": {},
        "ats": {
            "score": data.ats_analysis.ats_percentage,
            "checks_passed": data.ats_analysis.passed_checks,
            "checks_warning": data.ats_analysis.warning_checks,
            "checks_failed": data.ats_analysis.failed_checks,
            "contact": {
                "email": data.ats_analysis.contact_info.email,
                "phone": data.ats_analysis.contact_info.phone,
                "linkedin": data.ats_analysis.contact_info.linkedin,
                "github": data.ats_analysis.contact_info.github
            }
        },
        "impact": {
            "score": int(data.impact_analysis.overall_score * 100),
            "strong_verbs": data.impact_analysis.total_strong_verbs,
            "weak_phrases": data.impact_analysis.total_weak_verbs,
            "metrics": data.impact_analysis.total_metrics
        },
        "recommendations": data.hybrid_score.top_suggestions[:5]
    }
    
    if data.hybrid_score.skill_analysis:
        skill = data.hybrid_score.skill_analysis
        report["skills"] = {
            "must_have_matched": skill.must_have_matched,
            "must_have_missing": skill.must_have_missing,
            "nice_to_have_matched": skill.nice_to_have_matched,
            "nice_to_have_missing": skill.nice_to_have_missing,
            "coverage": {
                "must_have": int(skill.must_have_coverage * 100),
                "nice_to_have": int(skill.nice_to_have_coverage * 100)
            }
        }
    
    if data.role_recommendation:
        report["role_fit"] = [
            {
                "role": m.role_title,
                "alignment": m.alignment_percentage,
                "fit_level": m.fit_level
            }
            for m in data.role_recommendation.top_matches
        ]
    
    return json.dumps(report, indent=2)


def generate_text_report(data: ReportData) -> str:
    """Generate a plain text report."""
    lines = []
    
    lines.append("=" * 60)
    lines.append("           RESUME ANALYSIS REPORT")
    lines.append("=" * 60)
    lines.append(f"Generated: {data.generated_at}")
    if data.job_title:
        lines.append(f"Target Role: {data.job_title}")
    lines.append("")
    
    lines.append("-" * 60)
    lines.append(f"OVERALL SCORE: {data.hybrid_score.final_percentage}/100 ({data.hybrid_score.final_level.value})")
    lines.append("-" * 60)
    lines.append("")
    
    lines.append("SCORE BREAKDOWN:")
    for comp in data.hybrid_score.all_components:
        lines.append(f"  {comp.name}: {comp.percentage}% (weight: {int(comp.weight*100)}%)")
    lines.append("")
    
    lines.append("-" * 60)
    lines.append("ATS COMPATIBILITY")
    lines.append("-" * 60)
    lines.append(f"ATS Score: {data.ats_analysis.ats_percentage}%")
    lines.append(f"Passed: {data.ats_analysis.passed_checks} | Warnings: {data.ats_analysis.warning_checks} | Failed: {data.ats_analysis.failed_checks}")
    lines.append("")
    
    lines.append("-" * 60)
    lines.append("TOP RECOMMENDATIONS")
    lines.append("-" * 60)
    for i, sug in enumerate(data.hybrid_score.top_suggestions[:5], 1):
        lines.append(f"{i}. {sug}")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def create_pdf_report(data: ReportData) -> Optional[bytes]:
    """
    Generate a PDF report.
    Returns bytes that can be downloaded.
    
    Note: Requires reportlab or falls back to HTML.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2563eb')
        )
        story.append(Paragraph("Resume Analysis Report", title_style))
        story.append(Paragraph(f"Generated: {data.generated_at}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Overall Score
        score_style = ParagraphStyle(
            'Score',
            parent=styles['Heading1'],
            fontSize=36,
            alignment=1,  # Center
            textColor=colors.HexColor('#1e40af')
        )
        story.append(Paragraph(
            f"{data.hybrid_score.final_percentage}/100",
            score_style
        ))
        story.append(Paragraph(
            f"({data.hybrid_score.final_level.value})",
            ParagraphStyle('ScoreLevel', parent=styles['Normal'], alignment=1)
        ))
        story.append(Spacer(1, 30))
        
        # Score Breakdown Table
        story.append(Paragraph("Score Breakdown", styles['Heading2']))
        score_data = [['Component', 'Score', 'Weight']]
        for comp in data.hybrid_score.all_components:
            score_data.append([comp.name, f"{comp.percentage}%", f"{int(comp.weight*100)}%"])
        
        table = Table(score_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9fafb')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
        ]))
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Recommendations
        story.append(Paragraph("Top Recommendations", styles['Heading2']))
        for i, sug in enumerate(data.hybrid_score.top_suggestions[:5], 1):
            story.append(Paragraph(f"{i}. {sug}", styles['Normal']))
        
        doc.build(story)
        return buffer.getvalue()
        
    except ImportError:
        # Fallback: return HTML as bytes
        html = generate_html_report(data)
        return html.encode('utf-8')
