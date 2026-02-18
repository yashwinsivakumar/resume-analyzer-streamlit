"""
Role Recommendation Engine

Instead of forcing users to pick a role, this module:
- Analyzes resume against ALL available roles
- Returns alignment percentages for each role
- Suggests best-fit roles based on skills

Example output:
  Your profile aligns:
  - 72% with AI/ML Intern
  - 65% with Data Science Intern
  - 48% with Software Engineer Intern
"""

import json
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from .sections import ParsedResume, parse_resume
from .skills import analyze_skills_sectioned, get_all_skills_from_taxonomy, detect_skills


@dataclass
class RoleMatch:
    """Match result for a single role."""
    role_key: str
    role_title: str
    alignment_score: float  # 0-1
    must_have_matched: list[str]
    must_have_missing: list[str]
    nice_to_have_matched: list[str]
    nice_to_have_missing: list[str]
    
    @property
    def alignment_percentage(self) -> int:
        return int(round(self.alignment_score * 100))
    
    @property
    def must_have_coverage(self) -> float:
        total = len(self.must_have_matched) + len(self.must_have_missing)
        if total == 0:
            return 0.0
        return len(self.must_have_matched) / total
    
    @property
    def nice_to_have_coverage(self) -> float:
        total = len(self.nice_to_have_matched) + len(self.nice_to_have_missing)
        if total == 0:
            return 0.0
        return len(self.nice_to_have_matched) / total
    
    @property
    def fit_level(self) -> str:
        """Human-readable fit level."""
        if self.alignment_score >= 0.75:
            return "Excellent Fit"
        elif self.alignment_score >= 0.6:
            return "Good Fit"
        elif self.alignment_score >= 0.45:
            return "Moderate Fit"
        elif self.alignment_score >= 0.3:
            return "Partial Fit"
        else:
            return "Low Fit"
    
    @property
    def top_missing_skills(self) -> list[str]:
        """Get top 3 missing must-have skills."""
        return self.must_have_missing[:3]


@dataclass
class RoleRecommendation:
    """Complete role recommendation result."""
    matches: list[RoleMatch]
    resume_skills: set[str]  # All skills detected in resume
    
    @property
    def best_match(self) -> Optional[RoleMatch]:
        """Get highest-scoring role."""
        if not self.matches:
            return None
        return max(self.matches, key=lambda m: m.alignment_score)
    
    @property
    def top_matches(self) -> list[RoleMatch]:
        """Get top 3 matching roles."""
        sorted_matches = sorted(self.matches, key=lambda m: m.alignment_score, reverse=True)
        return sorted_matches[:3]
    
    @property
    def good_fit_roles(self) -> list[RoleMatch]:
        """Get all roles with >60% alignment."""
        return [m for m in self.matches if m.alignment_score >= 0.6]
    
    def get_role_match(self, role_key: str) -> Optional[RoleMatch]:
        """Get match for a specific role."""
        for match in self.matches:
            if match.role_key == role_key:
                return match
        return None


def calculate_role_alignment(
    resume_text: str,
    role_taxonomy: dict,
    parsed_resume: Optional[ParsedResume] = None
) -> RoleMatch:
    """
    Calculate alignment score for a single role.
    
    Args:
        resume_text: Full resume text
        role_taxonomy: Single role's taxonomy (with must_have, nice_to_have)
        parsed_resume: Optional pre-parsed resume
        
    Returns:
        RoleMatch with alignment details
    """
    if parsed_resume is None:
        parsed_resume = parse_resume(resume_text)
    
    # Analyze skills with section awareness
    skill_analysis = analyze_skills_sectioned(parsed_resume, role_taxonomy)
    
    # Calculate weighted alignment score
    # Must-have: 70% weight, Nice-to-have: 30% weight
    must_have_score = skill_analysis.must_have_coverage
    nice_to_have_score = skill_analysis.nice_to_have_coverage
    
    # Evidence bonus: skills proven in Experience/Projects get bonus
    evidence_bonus = skill_analysis.proven_skills_ratio * 0.1
    
    alignment_score = (must_have_score * 0.7 + nice_to_have_score * 0.3) + evidence_bonus
    alignment_score = min(1.0, alignment_score)  # Cap at 1.0
    
    return RoleMatch(
        role_key="",  # Will be set by caller
        role_title=role_taxonomy.get("title", "Unknown"),
        alignment_score=alignment_score,
        must_have_matched=skill_analysis.must_have_matched,
        must_have_missing=skill_analysis.must_have_missing,
        nice_to_have_matched=skill_analysis.nice_to_have_matched,
        nice_to_have_missing=skill_analysis.nice_to_have_missing
    )


def recommend_roles(
    resume_text: str,
    taxonomy: dict,
    parsed_resume: Optional[ParsedResume] = None
) -> RoleRecommendation:
    """
    Analyze resume against all roles and recommend best fits.
    
    Args:
        resume_text: Full resume text
        taxonomy: Full taxonomy with tracks containing roles
        parsed_resume: Optional pre-parsed resume
        
    Returns:
        RoleRecommendation with all role matches
    """
    if parsed_resume is None:
        parsed_resume = parse_resume(resume_text)
    
    matches = []
    all_skills = set()
    
    # Iterate through tracks and their roles
    for track_key, track_data in taxonomy.items():
        roles = track_data.get("roles", {})
        for role_key, role_data in roles.items():
            role_match = calculate_role_alignment(resume_text, role_data, parsed_resume)
            role_match.role_key = role_key
            matches.append(role_match)
            
            # Collect all matched skills
            all_skills.update(role_match.must_have_matched)
            all_skills.update(role_match.nice_to_have_matched)
    
    # Sort by alignment score (highest first)
    matches.sort(key=lambda m: m.alignment_score, reverse=True)
    
    return RoleRecommendation(
        matches=matches,
        resume_skills=all_skills
    )


def get_role_insights(recommendation: RoleRecommendation) -> dict:
    """
    Generate insights about the role recommendation.
    
    Returns dict with:
        - best_role: Best matching role
        - skill_strengths: Skills that appear across multiple roles
        - skill_gaps: Common missing skills
        - career_paths: Related roles to consider
    """
    if not recommendation.matches:
        return {}
    
    best = recommendation.best_match
    top_3 = recommendation.top_matches
    
    # Find skill strengths (skills matched in multiple roles)
    skill_counts = {}
    for match in recommendation.matches:
        for skill in match.must_have_matched + match.nice_to_have_matched:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    strengths = [skill for skill, count in skill_counts.items() if count >= 2]
    
    # Find common gaps (skills missing across top roles)
    gap_counts = {}
    for match in top_3:
        for skill in match.must_have_missing:
            gap_counts[skill] = gap_counts.get(skill, 0) + 1
    
    common_gaps = [skill for skill, count in gap_counts.items() if count >= 2]
    
    # Career paths (roles with good alignment)
    career_paths = [
        {"role": m.role_title, "alignment": m.alignment_percentage}
        for m in recommendation.good_fit_roles
    ]
    
    return {
        "best_role": {
            "title": best.role_title,
            "alignment": best.alignment_percentage,
            "fit_level": best.fit_level
        },
        "skill_strengths": strengths[:5],
        "skill_gaps": common_gaps[:5],
        "career_paths": career_paths
    }


def get_recommendation_summary(recommendation: RoleRecommendation) -> str:
    """Generate text summary of role recommendation."""
    if not recommendation.matches:
        return "No roles available for comparison."
    
    lines = ["Your profile alignment:"]
    lines.append("")
    
    for match in recommendation.top_matches:
        lines.append(
            f"  {match.alignment_percentage}% - {match.role_title} ({match.fit_level})"
        )
    
    best = recommendation.best_match
    if best:
        lines.append("")
        lines.append(f"Best fit: {best.role_title}")
        
        if best.top_missing_skills:
            missing = ", ".join(s.replace("_", " ").title() for s in best.top_missing_skills)
            lines.append(f"To improve: Add {missing}")
    
    return "\n".join(lines)


def quick_role_match(resume_text: str, taxonomy_path: str = "data/skills_taxonomy.json") -> dict:
    """
    Quick utility function for role matching.
    
    Returns dict with role percentages, useful for display.
    """
    try:
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            taxonomy = json.load(f)
    except FileNotFoundError:
        return {"error": "Taxonomy file not found"}
    
    recommendation = recommend_roles(resume_text, taxonomy)
    
    return {
        match.role_title: match.alignment_percentage
        for match in recommendation.matches
    }
