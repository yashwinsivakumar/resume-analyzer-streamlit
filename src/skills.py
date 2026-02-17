"""
Skill Intelligence Engine

Enhanced skill detection with:
- Section-aware detection
- Evidence mapping with confidence scores
- Skill weighting (must_have vs nice_to_have)
- Alias-based matching with fuzzy fallback
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from rapidfuzz import fuzz

from .sections import ParsedResume, SectionType, Section, SECTION_WEIGHTS


class SkillPriority(Enum):
    """Priority level of a skill."""
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"


class DetectionConfidence(Enum):
    """Confidence level of skill detection."""
    HIGH = "high"      # Exact match found
    MEDIUM = "medium"  # Fuzzy match found
    LOW = "low"        # Weak/uncertain match


@dataclass
class SkillEvidence:
    """Evidence of a skill found in resume."""
    section_type: SectionType
    section_name: str
    snippet: str
    matched_alias: str
    position: int  # Character position in section
    
    @property
    def weight(self) -> float:
        """Get evidence weight based on section."""
        return SECTION_WEIGHTS.get(self.section_type, 0.3)


@dataclass
class DetectedSkill:
    """A detected skill with all metadata."""
    skill_id: str
    skill_name: str
    priority: SkillPriority
    weight: float
    category: str
    confidence: DetectionConfidence
    evidence_list: list[SkillEvidence] = field(default_factory=list)
    
    @property
    def best_evidence(self) -> Optional[SkillEvidence]:
        """Get the highest-weighted evidence."""
        if not self.evidence_list:
            return None
        return max(self.evidence_list, key=lambda e: e.weight)
    
    @property
    def evidence_score(self) -> float:
        """Calculate evidence score (0-1) based on where skill was found."""
        if not self.evidence_list:
            return 0.0
        # Use best evidence weight
        best = self.best_evidence
        return best.weight if best else 0.0
    
    @property
    def is_proven(self) -> bool:
        """Check if skill is proven in Experience/Projects (not just listed)."""
        proven_sections = {SectionType.EXPERIENCE, SectionType.PROJECTS, SectionType.CERTIFICATIONS}
        return any(e.section_type in proven_sections for e in self.evidence_list)
    
    @property
    def is_only_listed(self) -> bool:
        """Check if skill is only listed in Skills section."""
        if not self.evidence_list:
            return False
        listed_sections = {SectionType.SKILLS, SectionType.SUMMARY}
        return all(e.section_type in listed_sections for e in self.evidence_list)


@dataclass
class SkillAnalysisResult:
    """Complete skill analysis result."""
    detected_skills: dict[str, DetectedSkill]
    must_have_matched: list[str]
    must_have_missing: list[str]
    nice_to_have_matched: list[str]
    nice_to_have_missing: list[str]
    
    @property
    def must_have_coverage(self) -> float:
        """Percentage of must-have skills matched."""
        total = len(self.must_have_matched) + len(self.must_have_missing)
        if total == 0:
            return 0.0
        return len(self.must_have_matched) / total
    
    @property
    def nice_to_have_coverage(self) -> float:
        """Percentage of nice-to-have skills matched."""
        total = len(self.nice_to_have_matched) + len(self.nice_to_have_missing)
        if total == 0:
            return 0.0
        return len(self.nice_to_have_matched) / total
    
    @property
    def overall_coverage(self) -> float:
        """Weighted overall skill coverage."""
        # Must-have weighted 70%, nice-to-have 30%
        return self.must_have_coverage * 0.7 + self.nice_to_have_coverage * 0.3
    
    @property
    def proven_skills_ratio(self) -> float:
        """Ratio of skills that are proven (not just listed)."""
        if not self.detected_skills:
            return 0.0
        proven = sum(1 for s in self.detected_skills.values() if s.is_proven)
        return proven / len(self.detected_skills)
    
    def get_skills_by_category(self) -> dict[str, list[DetectedSkill]]:
        """Group detected skills by category."""
        categories: dict[str, list[DetectedSkill]] = {}
        for skill in self.detected_skills.values():
            if skill.category not in categories:
                categories[skill.category] = []
            categories[skill.category].append(skill)
        return categories


def find_evidence_in_section(section: Section, aliases: list[str]) -> list[SkillEvidence]:
    """Find all evidence of skill aliases in a section."""
    evidence_list = []
    text_lower = section.content.lower()
    
    for alias in aliases:
        alias_lower = alias.lower()
        pattern = r"\b" + re.escape(alias_lower) + r"\b"
        
        for match in re.finditer(pattern, text_lower):
            # Extract snippet around the match
            start = max(0, match.start() - 50)
            end = min(len(section.content), match.end() + 50)
            snippet = "..." + section.content[start:end].strip() + "..."
            
            evidence_list.append(SkillEvidence(
                section_type=section.section_type,
                section_name=section.heading or section.section_type.value,
                snippet=snippet,
                matched_alias=alias,
                position=match.start()
            ))
    
    return evidence_list


def detect_skill_in_text(text: str, aliases: list[str], fuzzy_threshold: int = 85) -> tuple[Optional[str], DetectionConfidence]:
    """
    Detect if any alias is present in text.
    Returns (matched_alias, confidence) or (None, None).
    """
    text_lower = text.lower()
    
    # Try exact boundary match first
    for alias in aliases:
        pattern = r"\b" + re.escape(alias.lower()) + r"\b"
        if re.search(pattern, text_lower):
            return alias, DetectionConfidence.HIGH
    
    # Try fuzzy match for longer aliases
    for alias in aliases:
        if len(alias) >= 4:
            ratio = fuzz.partial_ratio(alias.lower(), text_lower)
            if ratio >= fuzzy_threshold:
                return alias, DetectionConfidence.MEDIUM
    
    return None, DetectionConfidence.LOW


def analyze_skills_sectioned(
    parsed_resume: ParsedResume,
    role_taxonomy: dict
) -> SkillAnalysisResult:
    """
    Analyze skills with section awareness.
    
    Args:
        parsed_resume: Parsed resume with sections
        role_taxonomy: Role taxonomy with must_have and nice_to_have skills
        
    Returns:
        SkillAnalysisResult with detailed skill analysis
    """
    detected_skills = {}
    must_have_matched = []
    must_have_missing = []
    nice_to_have_matched = []
    nice_to_have_missing = []
    
    # Process must-have skills
    must_have = role_taxonomy.get("must_have", {})
    for skill_id, skill_info in must_have.items():
        aliases = skill_info.get("aliases", [])
        weight = skill_info.get("weight", 1.0)
        category = skill_info.get("category", "other")
        
        all_evidence = []
        best_confidence = DetectionConfidence.LOW
        
        # Search in each section
        for section in parsed_resume.sections:
            evidence = find_evidence_in_section(section, aliases)
            if evidence:
                all_evidence.extend(evidence)
                # Update confidence based on exact match
                _, conf = detect_skill_in_text(section.content, aliases)
                if conf == DetectionConfidence.HIGH:
                    best_confidence = DetectionConfidence.HIGH
                elif conf == DetectionConfidence.MEDIUM and best_confidence != DetectionConfidence.HIGH:
                    best_confidence = DetectionConfidence.MEDIUM
        
        if all_evidence:
            detected_skills[skill_id] = DetectedSkill(
                skill_id=skill_id,
                skill_name=skill_id.replace("_", " ").title(),
                priority=SkillPriority.MUST_HAVE,
                weight=weight,
                category=category,
                confidence=best_confidence,
                evidence_list=all_evidence
            )
            must_have_matched.append(skill_id)
        else:
            must_have_missing.append(skill_id)
    
    # Process nice-to-have skills
    nice_to_have = role_taxonomy.get("nice_to_have", {})
    for skill_id, skill_info in nice_to_have.items():
        aliases = skill_info.get("aliases", [])
        weight = skill_info.get("weight", 0.5)
        category = skill_info.get("category", "other")
        
        all_evidence = []
        best_confidence = DetectionConfidence.LOW
        
        # Search in each section
        for section in parsed_resume.sections:
            evidence = find_evidence_in_section(section, aliases)
            if evidence:
                all_evidence.extend(evidence)
                _, conf = detect_skill_in_text(section.content, aliases)
                if conf == DetectionConfidence.HIGH:
                    best_confidence = DetectionConfidence.HIGH
                elif conf == DetectionConfidence.MEDIUM and best_confidence != DetectionConfidence.HIGH:
                    best_confidence = DetectionConfidence.MEDIUM
        
        if all_evidence:
            detected_skills[skill_id] = DetectedSkill(
                skill_id=skill_id,
                skill_name=skill_id.replace("_", " ").title(),
                priority=SkillPriority.NICE_TO_HAVE,
                weight=weight,
                category=category,
                confidence=best_confidence,
                evidence_list=all_evidence
            )
            nice_to_have_matched.append(skill_id)
        else:
            nice_to_have_missing.append(skill_id)
    
    return SkillAnalysisResult(
        detected_skills=detected_skills,
        must_have_matched=must_have_matched,
        must_have_missing=must_have_missing,
        nice_to_have_matched=nice_to_have_matched,
        nice_to_have_missing=nice_to_have_missing
    )


# ============ Legacy compatibility functions ============

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
    Legacy skill detection function for backward compatibility.
    Detect skills in text using exact and fuzzy matching.
    
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


def get_all_skills_from_taxonomy(role_taxonomy: dict) -> dict[str, list[str]]:
    """
    Convert new taxonomy format to legacy skill_map format.
    Combines must_have and nice_to_have into single dict.
    """
    skill_map = {}
    
    for priority in ["must_have", "nice_to_have"]:
        skills = role_taxonomy.get(priority, {})
        for skill_id, skill_info in skills.items():
            skill_map[skill_id] = skill_info.get("aliases", [])
    
    return skill_map

