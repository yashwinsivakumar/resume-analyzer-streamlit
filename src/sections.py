"""
Resume Section Parser

Detects and extracts structured sections from resume text.
This enables section-aware skill detection and evidence weighting.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SectionType(Enum):
    """Types of resume sections."""
    SUMMARY = "summary"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    PROJECTS = "projects"
    EDUCATION = "education"
    CERTIFICATIONS = "certifications"
    AWARDS = "awards"
    PUBLICATIONS = "publications"
    CONTACT = "contact"
    OTHER = "other"


# Section detection patterns (heading variations)
SECTION_PATTERNS = {
    SectionType.SUMMARY: [
        r"(?:professional\s+)?summary",
        r"(?:career\s+)?objective",
        r"profile",
        r"about\s*(?:me)?",
        r"executive\s+summary",
        r"personal\s+statement",
    ],
    SectionType.SKILLS: [
        r"(?:technical\s+)?skills",
        r"technologies",
        r"competencies",
        r"expertise",
        r"proficiencies",
        r"tools?\s*(?:&|and)?\s*technologies",
        r"technical\s+proficiency",
        r"core\s+competencies",
    ],
    SectionType.EXPERIENCE: [
        r"(?:work|professional|employment)\s*(?:experience|history)?",
        r"experience",
        r"career\s+history",
        r"work\s+history",
        r"professional\s+background",
        r"positions?\s+held",
    ],
    SectionType.PROJECTS: [
        r"projects?",
        r"(?:personal|academic|professional)\s+projects?",
        r"portfolio",
        r"key\s+projects?",
        r"selected\s+projects?",
    ],
    SectionType.EDUCATION: [
        r"education(?:al\s+background)?",
        r"academic\s+(?:background|qualifications?)",
        r"qualifications?",
        r"degrees?",
        r"academic\s+history",
    ],
    SectionType.CERTIFICATIONS: [
        r"certifications?",
        r"licenses?\s*(?:&|and)?\s*certifications?",
        r"professional\s+certifications?",
        r"credentials?",
        r"accreditations?",
    ],
    SectionType.AWARDS: [
        r"awards?\s*(?:&|and)?\s*(?:honors?|achievements?)?",
        r"honors?\s*(?:&|and)?\s*awards?",
        r"achievements?",
        r"recognition",
        r"accomplishments?",
    ],
    SectionType.PUBLICATIONS: [
        r"publications?",
        r"papers?",
        r"research(?:\s+papers?)?",
        r"articles?",
    ],
    SectionType.CONTACT: [
        r"contact(?:\s+(?:info(?:rmation)?|details?))?",
        r"personal\s+(?:info(?:rmation)?|details?)",
    ],
}

# Section importance weights for evidence scoring
SECTION_WEIGHTS = {
    SectionType.EXPERIENCE: 1.0,     # Proven in work
    SectionType.PROJECTS: 0.9,       # Demonstrated in projects
    SectionType.CERTIFICATIONS: 0.8, # Certified
    SectionType.SKILLS: 0.5,         # Listed only (less weight)
    SectionType.EDUCATION: 0.6,      # Academic background
    SectionType.SUMMARY: 0.4,        # Self-reported
    SectionType.AWARDS: 0.7,         # Recognition
    SectionType.PUBLICATIONS: 0.8,   # Published work
    SectionType.OTHER: 0.3,          # Unknown context
    SectionType.CONTACT: 0.0,        # No skill value
}


@dataclass
class Section:
    """A parsed resume section."""
    section_type: SectionType
    heading: str
    content: str
    start_pos: int
    end_pos: int
    weight: float = field(init=False)
    
    def __post_init__(self):
        self.weight = SECTION_WEIGHTS.get(self.section_type, 0.3)
    
    @property
    def word_count(self) -> int:
        return len(self.content.split())
    
    @property
    def has_bullets(self) -> bool:
        return bool(re.search(r'[•\-\*]', self.content))


@dataclass
class ParsedResume:
    """A fully parsed resume with structured sections."""
    original_text: str
    sections: list[Section]
    
    def get_section(self, section_type: SectionType) -> Optional[Section]:
        """Get the first section of a given type."""
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None
    
    def get_sections(self, section_type: SectionType) -> list[Section]:
        """Get all sections of a given type."""
        return [s for s in self.sections if s.section_type == section_type]
    
    def get_combined_text(self, *section_types: SectionType) -> str:
        """Get combined text from specified section types."""
        texts = []
        for section in self.sections:
            if section.section_type in section_types:
                texts.append(section.content)
        return "\n".join(texts)
    
    @property
    def has_experience(self) -> bool:
        return any(s.section_type == SectionType.EXPERIENCE for s in self.sections)
    
    @property
    def has_projects(self) -> bool:
        return any(s.section_type == SectionType.PROJECTS for s in self.sections)
    
    @property
    def has_skills(self) -> bool:
        return any(s.section_type == SectionType.SKILLS for s in self.sections)
    
    @property
    def has_education(self) -> bool:
        return any(s.section_type == SectionType.EDUCATION for s in self.sections)
    
    def get_section_balance(self) -> dict[str, float]:
        """Calculate content distribution across sections."""
        total_words = sum(s.word_count for s in self.sections)
        if total_words == 0:
            return {}
        return {
            s.section_type.value: round(s.word_count / total_words * 100, 1)
            for s in self.sections
        }


def _create_section_pattern() -> re.Pattern:
    """Create a compiled regex pattern to detect section headings."""
    all_patterns = []
    for patterns in SECTION_PATTERNS.values():
        all_patterns.extend(patterns)
    
    # Match section headings at start of line, possibly with formatting chars
    combined = "|".join(all_patterns)
    pattern = rf"^\s*[#\*\-•]?\s*(?:{combined})\s*[:\-–—]?\s*$"
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE)


def _identify_section_type(heading: str) -> SectionType:
    """Identify the section type from a heading."""
    heading_lower = heading.lower().strip()
    # Remove common formatting
    heading_clean = re.sub(r'^[#\*\-•:\s]+|[:\-–—\s]+$', '', heading_lower)
    
    for section_type, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.match(rf"^{pattern}$", heading_clean, re.IGNORECASE):
                return section_type
    
    return SectionType.OTHER


def parse_resume(text: str) -> ParsedResume:
    """
    Parse resume text into structured sections.
    
    Args:
        text: Raw resume text
        
    Returns:
        ParsedResume object with detected sections
    """
    sections = []
    section_pattern = _create_section_pattern()
    
    # Find all potential section headings
    matches = list(section_pattern.finditer(text))
    
    if not matches:
        # No sections detected - treat entire text as "other"
        return ParsedResume(
            original_text=text,
            sections=[Section(
                section_type=SectionType.OTHER,
                heading="",
                content=text,
                start_pos=0,
                end_pos=len(text)
            )]
        )
    
    # Extract content between section headings
    for i, match in enumerate(matches):
        heading = match.group().strip()
        section_type = _identify_section_type(heading)
        start_pos = match.end()
        
        # Find end position (start of next section or end of text)
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(text)
        
        content = text[start_pos:end_pos].strip()
        
        if content:  # Only add non-empty sections
            sections.append(Section(
                section_type=section_type,
                heading=heading,
                content=content,
                start_pos=start_pos,
                end_pos=end_pos
            ))
    
    # Handle content before first section (often contact info)
    if matches and matches[0].start() > 50:
        pre_content = text[:matches[0].start()].strip()
        if pre_content:
            sections.insert(0, Section(
                section_type=SectionType.CONTACT,
                heading="",
                content=pre_content,
                start_pos=0,
                end_pos=matches[0].start()
            ))
    
    return ParsedResume(original_text=text, sections=sections)


def get_evidence_sections() -> tuple[SectionType, ...]:
    """Get section types that provide strong evidence for skills."""
    return (SectionType.EXPERIENCE, SectionType.PROJECTS, SectionType.CERTIFICATIONS)


def get_listed_sections() -> tuple[SectionType, ...]:
    """Get section types where skills are typically just listed."""
    return (SectionType.SKILLS, SectionType.SUMMARY)


def calculate_section_completeness(parsed: ParsedResume) -> dict[str, bool]:
    """Check which essential sections are present."""
    return {
        "has_contact": bool(parsed.get_section(SectionType.CONTACT)),
        "has_summary": bool(parsed.get_section(SectionType.SUMMARY)),
        "has_experience": parsed.has_experience,
        "has_education": parsed.has_education,
        "has_skills": parsed.has_skills,
        "has_projects": parsed.has_projects,
    }
