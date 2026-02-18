"""
ATS (Applicant Tracking System) Simulation

Comprehensive checks that simulate how ATS systems parse and evaluate resumes:
- Keyword density analysis
- Resume length optimization
- Bullet point structure
- Contact information detection
- Professional links (GitHub, LinkedIn)
- Section balance and completeness
- Formatting issues detection
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .sections import ParsedResume, SectionType, calculate_section_completeness


class ATSCheckStatus(Enum):
    """Status of an ATS check."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass
class ATSCheck:
    """Individual ATS check result."""
    name: str
    status: ATSCheckStatus
    message: str
    details: Optional[str] = None
    suggestion: Optional[str] = None
    
    @property
    def icon(self) -> str:
        if self.status == ATSCheckStatus.PASS:
            return "✅"
        elif self.status == ATSCheckStatus.WARNING:
            return "⚠️"
        else:
            return "❌"


@dataclass
class ContactInfo:
    """Detected contact information."""
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None


@dataclass
class ATSAnalysis:
    """Complete ATS analysis result."""
    checks: list[ATSCheck]
    contact_info: ContactInfo
    keyword_density: dict[str, int]
    
    # Scores
    ats_score: float  # 0-1
    parseability_score: float  # How well ATS can parse
    completeness_score: float  # Section completeness
    
    @property
    def passed_checks(self) -> int:
        return sum(1 for c in self.checks if c.status == ATSCheckStatus.PASS)
    
    @property
    def warning_checks(self) -> int:
        return sum(1 for c in self.checks if c.status == ATSCheckStatus.WARNING)
    
    @property
    def failed_checks(self) -> int:
        return sum(1 for c in self.checks if c.status == ATSCheckStatus.FAIL)
    
    @property
    def total_checks(self) -> int:
        return len(self.checks)
    
    @property
    def ats_percentage(self) -> int:
        return int(round(self.ats_score * 100))
    
    @property
    def critical_issues(self) -> list[ATSCheck]:
        return [c for c in self.checks if c.status == ATSCheckStatus.FAIL]
    
    @property
    def warnings(self) -> list[ATSCheck]:
        return [c for c in self.checks if c.status == ATSCheckStatus.WARNING]


# ============ Check Functions ============

def check_resume_length(text: str) -> ATSCheck:
    """Check if resume length is optimal."""
    word_count = len(text.split())
    char_count = len(text)
    
    if word_count < 200:
        return ATSCheck(
            name="Resume Length",
            status=ATSCheckStatus.FAIL,
            message=f"Resume too short ({word_count} words)",
            details="Most ATS and recruiters expect at least 300-400 words",
            suggestion="Add more details about your experience, projects, and skills"
        )
    elif word_count < 350:
        return ATSCheck(
            name="Resume Length",
            status=ATSCheckStatus.WARNING,
            message=f"Resume may be short ({word_count} words)",
            details="Consider adding more content for better ATS scoring",
            suggestion="Expand on your achievements and responsibilities"
        )
    elif word_count > 1200:
        return ATSCheck(
            name="Resume Length",
            status=ATSCheckStatus.WARNING,
            message=f"Resume may be too long ({word_count} words)",
            details="Long resumes may lose recruiter attention",
            suggestion="Consider condensing to most relevant experience (1-2 pages)"
        )
    else:
        return ATSCheck(
            name="Resume Length",
            status=ATSCheckStatus.PASS,
            message=f"Good length ({word_count} words)",
            details="Resume length is optimal for ATS and recruiter review"
        )


def check_bullet_points(text: str) -> ATSCheck:
    """Check bullet point usage."""
    bullet_patterns = [r'•', r'^\s*[-–—]\s', r'^\s*\*\s', r'^\s*\d+\.\s']
    
    bullet_count = 0
    for pattern in bullet_patterns:
        bullet_count += len(re.findall(pattern, text, re.MULTILINE))
    
    if bullet_count < 5:
        return ATSCheck(
            name="Bullet Points",
            status=ATSCheckStatus.WARNING,
            message=f"Few bullet points detected ({bullet_count})",
            details="Bullet points help ATS parse content and improve readability",
            suggestion="Use bullet points for responsibilities and achievements"
        )
    elif bullet_count > 40:
        return ATSCheck(
            name="Bullet Points",
            status=ATSCheckStatus.WARNING,
            message=f"Many bullet points ({bullet_count})",
            details="Too many bullets may indicate lack of prioritization",
            suggestion="Focus on most impactful 3-5 bullets per role"
        )
    else:
        return ATSCheck(
            name="Bullet Points",
            status=ATSCheckStatus.PASS,
            message=f"Good bullet usage ({bullet_count} bullets)",
            details="Well-structured content improves ATS parsing"
        )


def detect_contact_info(text: str) -> ContactInfo:
    """Extract contact information from resume."""
    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group(0) if email_match else None
    
    # Phone (various formats)
    phone_patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\d{10}',
    ]
    phone = None
    for pattern in phone_patterns:
        phone_match = re.search(pattern, text)
        if phone_match:
            phone = phone_match.group(0)
            break
    
    # LinkedIn
    linkedin_match = re.search(
        r'(?:linkedin\.com/in/|linkedin:\s*@?)([a-zA-Z0-9-]+)',
        text, re.IGNORECASE
    )
    linkedin = linkedin_match.group(0) if linkedin_match else None
    
    # GitHub
    github_match = re.search(
        r'(?:github\.com/|github:\s*@?)([a-zA-Z0-9-]+)',
        text, re.IGNORECASE
    )
    github = github_match.group(0) if github_match else None
    
    # Website/Portfolio
    website_match = re.search(
        r'(?:portfolio|website|site):\s*(https?://[\w\.-]+\.\w+[/\w]*)',
        text, re.IGNORECASE
    )
    if not website_match:
        website_match = re.search(
            r'(https?://[\w\.-]+\.\w+)',
            text
        )
    website = website_match.group(1) if website_match else None
    
    return ContactInfo(
        email=email,
        phone=phone,
        linkedin=linkedin,
        github=github,
        website=website
    )


def check_contact_info(contact: ContactInfo) -> list[ATSCheck]:
    """Check contact information completeness."""
    checks = []
    
    # Email check
    if contact.email:
        checks.append(ATSCheck(
            name="Email",
            status=ATSCheckStatus.PASS,
            message="Email detected",
            details=contact.email
        ))
    else:
        checks.append(ATSCheck(
            name="Email",
            status=ATSCheckStatus.FAIL,
            message="No email found",
            details="ATS systems need an email to process your application",
            suggestion="Add your professional email address"
        ))
    
    # Phone check
    if contact.phone:
        checks.append(ATSCheck(
            name="Phone",
            status=ATSCheckStatus.PASS,
            message="Phone number detected",
            details=contact.phone
        ))
    else:
        checks.append(ATSCheck(
            name="Phone",
            status=ATSCheckStatus.WARNING,
            message="No phone number found",
            suggestion="Consider adding a phone number"
        ))
    
    # LinkedIn check
    if contact.linkedin:
        checks.append(ATSCheck(
            name="LinkedIn",
            status=ATSCheckStatus.PASS,
            message="LinkedIn profile detected",
            details=contact.linkedin
        ))
    else:
        checks.append(ATSCheck(
            name="LinkedIn",
            status=ATSCheckStatus.WARNING,
            message="No LinkedIn profile found",
            suggestion="Add your LinkedIn URL for better professional presence"
        ))
    
    # GitHub check (important for tech roles)
    if contact.github:
        checks.append(ATSCheck(
            name="GitHub",
            status=ATSCheckStatus.PASS,
            message="GitHub profile detected",
            details=contact.github
        ))
    else:
        checks.append(ATSCheck(
            name="GitHub",
            status=ATSCheckStatus.WARNING,
            message="No GitHub profile found",
            suggestion="Add GitHub link to showcase your code (especially for tech roles)"
        ))
    
    return checks


def check_section_completeness(parsed_resume: ParsedResume) -> ATSCheck:
    """Check if essential sections are present."""
    completeness = calculate_section_completeness(parsed_resume)
    
    missing = []
    if not completeness.get("has_experience"):
        missing.append("Experience")
    if not completeness.get("has_education"):
        missing.append("Education")
    if not completeness.get("has_skills"):
        missing.append("Skills")
    
    if len(missing) >= 2:
        return ATSCheck(
            name="Section Completeness",
            status=ATSCheckStatus.FAIL,
            message=f"Missing key sections: {', '.join(missing)}",
            details="ATS systems expect standard resume sections",
            suggestion=f"Add clear {', '.join(missing)} section(s)"
        )
    elif len(missing) == 1:
        return ATSCheck(
            name="Section Completeness",
            status=ATSCheckStatus.WARNING,
            message=f"Missing section: {missing[0]}",
            suggestion=f"Consider adding a {missing[0]} section"
        )
    else:
        return ATSCheck(
            name="Section Completeness",
            status=ATSCheckStatus.PASS,
            message="All essential sections present",
            details="Experience, Education, and Skills sections detected"
        )


def check_section_balance(parsed_resume: ParsedResume) -> ATSCheck:
    """Check if section sizes are balanced."""
    balance = parsed_resume.get_section_balance()
    
    exp_pct = balance.get("experience", 0)
    skills_pct = balance.get("skills", 0)
    edu_pct = balance.get("education", 0)
    
    issues = []
    if exp_pct < 20:
        issues.append("Experience section too brief")
    if exp_pct > 80:
        issues.append("Experience section dominates resume")
    if skills_pct > 40:
        issues.append("Skills section may be too long (consider pruning)")
    
    if issues:
        return ATSCheck(
            name="Section Balance",
            status=ATSCheckStatus.WARNING,
            message="; ".join(issues),
            details=f"Experience: {exp_pct}%, Skills: {skills_pct}%, Education: {edu_pct}%",
            suggestion="Balance content across sections"
        )
    else:
        return ATSCheck(
            name="Section Balance",
            status=ATSCheckStatus.PASS,
            message="Sections are well-balanced",
            details=f"Experience: {exp_pct}%, Skills: {skills_pct}%, Education: {edu_pct}%"
        )


def check_keyword_density(text: str, jd_text: Optional[str] = None) -> tuple[ATSCheck, dict]:
    """Analyze keyword density and JD alignment."""
    # Common technical/professional keywords
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    top_keywords = dict(sorted_keywords[:20])
    
    # Check for keyword stuffing
    total_words = len(words)
    top_word_count = sorted_keywords[0][1] if sorted_keywords else 0
    
    if top_word_count > total_words * 0.1:  # Single word > 10% of content
        return ATSCheck(
            name="Keyword Density",
            status=ATSCheckStatus.WARNING,
            message=f"Possible keyword stuffing detected ('{sorted_keywords[0][0]}')",
            details="ATS may flag resumes with unnatural keyword repetition",
            suggestion="Use keywords naturally in context, not repeated lists"
        ), top_keywords
    
    return ATSCheck(
        name="Keyword Density",
        status=ATSCheckStatus.PASS,
        message="Natural keyword distribution",
        details=f"Top keywords: {', '.join(list(top_keywords.keys())[:5])}"
    ), top_keywords


def check_formatting_issues(text: str) -> ATSCheck:
    """Check for common formatting issues."""
    issues = []
    
    # Check for special characters that may confuse ATS
    special_chars = len(re.findall(r'[^\w\s\-.,;:!?@#$%&*()\[\]{}\'\"<>/\\|+=]', text))
    if special_chars > 20:
        issues.append("Unusual special characters detected")
    
    # Check for all-caps sections (hard to read)
    caps_matches = re.findall(r'\b[A-Z]{10,}\b', text)
    if len(caps_matches) > 3:
        issues.append("Excessive use of ALL CAPS")
    
    # Check for very long lines (possible formatting issues)
    lines = text.split('\n')
    long_lines = sum(1 for line in lines if len(line) > 200)
    if long_lines > 5:
        issues.append("Very long lines detected (possible copy-paste issues)")
    
    if issues:
        return ATSCheck(
            name="Formatting",
            status=ATSCheckStatus.WARNING,
            message="; ".join(issues),
            suggestion="Clean up formatting for better ATS parsing"
        )
    
    return ATSCheck(
        name="Formatting",
        status=ATSCheckStatus.PASS,
        message="No major formatting issues detected"
    )


def check_date_formats(text: str) -> ATSCheck:
    """Check for consistent date formatting."""
    date_patterns = [
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',
        r'\b\d{1,2}/\d{4}\b',
        r'\b\d{4}\s*[-–]\s*(?:\d{4}|Present|Current)\b',
    ]
    
    dates_found = []
    for pattern in date_patterns:
        dates_found.extend(re.findall(pattern, text, re.IGNORECASE))
    
    if len(dates_found) < 2:
        return ATSCheck(
            name="Date Formatting",
            status=ATSCheckStatus.WARNING,
            message="Few dates detected",
            suggestion="Include dates for experience and education (e.g., 'Jan 2023 - Present')"
        )
    
    return ATSCheck(
        name="Date Formatting",
        status=ATSCheckStatus.PASS,
        message=f"Dates detected ({len(dates_found)} found)",
        details="Helps ATS understand your timeline"
    )


# ============ Main Analysis Function ============

def analyze_ats(
    text: str,
    parsed_resume: Optional[ParsedResume] = None,
    jd_text: Optional[str] = None
) -> ATSAnalysis:
    """
    Perform comprehensive ATS analysis.
    
    Args:
        text: Full resume text
        parsed_resume: Optional pre-parsed resume
        jd_text: Optional job description for keyword matching
        
    Returns:
        ATSAnalysis with all checks and scores
    """
    from .sections import parse_resume
    
    if parsed_resume is None:
        parsed_resume = parse_resume(text)
    
    checks = []
    
    # Basic checks
    checks.append(check_resume_length(text))
    checks.append(check_bullet_points(text))
    checks.append(check_formatting_issues(text))
    checks.append(check_date_formats(text))
    
    # Contact info checks
    contact_info = detect_contact_info(text)
    checks.extend(check_contact_info(contact_info))
    
    # Section checks
    checks.append(check_section_completeness(parsed_resume))
    if parsed_resume.sections:
        checks.append(check_section_balance(parsed_resume))
    
    # Keyword analysis
    keyword_check, keyword_density = check_keyword_density(text, jd_text)
    checks.append(keyword_check)
    
    # Calculate scores
    passed = sum(1 for c in checks if c.status == ATSCheckStatus.PASS)
    warnings = sum(1 for c in checks if c.status == ATSCheckStatus.WARNING)
    failed = sum(1 for c in checks if c.status == ATSCheckStatus.FAIL)
    total = len(checks)
    
    # ATS score: pass=1, warning=0.5, fail=0
    ats_score = (passed + warnings * 0.5) / total if total > 0 else 0
    
    # Parseability: based on critical issues
    critical_checks = ["Email", "Section Completeness", "Resume Length"]
    critical_passed = sum(
        1 for c in checks 
        if c.name in critical_checks and c.status == ATSCheckStatus.PASS
    )
    parseability_score = critical_passed / len(critical_checks)
    
    # Completeness score
    completeness = calculate_section_completeness(parsed_resume)
    completeness_score = sum(completeness.values()) / len(completeness)
    
    return ATSAnalysis(
        checks=checks,
        contact_info=contact_info,
        keyword_density=keyword_density,
        ats_score=ats_score,
        parseability_score=parseability_score,
        completeness_score=completeness_score
    )


# ============ Legacy Function ============

def basic_ats_checks(resume_text: str) -> list[str]:
    """Legacy function for backward compatibility."""
    analysis = analyze_ats(resume_text)
    
    warnings = []
    for check in analysis.checks:
        if check.status in [ATSCheckStatus.WARNING, ATSCheckStatus.FAIL]:
            msg = f"{check.icon} {check.message}"
            if check.suggestion:
                msg += f" - {check.suggestion}"
            warnings.append(msg)
    
    return warnings if warnings else ["✅ No major ATS issues detected"]

