"""
Hybrid Scoring Engine

Combines multiple scoring dimensions into a professional, explainable score.

Final Score Formula:
  40% Skill Coverage
+ 30% Semantic Similarity  
+ 20% Evidence Strength
+ 10% Impact Quality

This creates a realistic, multi-dimensional assessment.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .sections import ParsedResume, SectionType, parse_resume
from .skills import SkillAnalysisResult, analyze_skills_sectioned
from .semantic import semantic_similarity, SemanticMatch, semantic_similarity_sectioned


class ScoreLevel(Enum):
    """Human-readable score levels."""
    EXCELLENT = "Excellent"
    GOOD = "Good"
    MODERATE = "Moderate"
    NEEDS_WORK = "Needs Work"
    POOR = "Poor"


@dataclass
class ScoreComponent:
    """A single score component with metadata."""
    name: str
    score: float  # 0.0 to 1.0
    weight: float  # Weight in final calculation
    details: str
    suggestions: list[str] = field(default_factory=list)
    
    @property
    def weighted_score(self) -> float:
        return self.score * self.weight
    
    @property
    def percentage(self) -> int:
        return int(round(self.score * 100))
    
    @property
    def level(self) -> ScoreLevel:
        if self.score >= 0.8:
            return ScoreLevel.EXCELLENT
        elif self.score >= 0.6:
            return ScoreLevel.GOOD
        elif self.score >= 0.4:
            return ScoreLevel.MODERATE
        elif self.score >= 0.2:
            return ScoreLevel.NEEDS_WORK
        else:
            return ScoreLevel.POOR


@dataclass
class HybridScore:
    """Complete hybrid scoring result."""
    skill_coverage: ScoreComponent
    semantic_similarity: ScoreComponent
    evidence_strength: ScoreComponent
    impact_quality: ScoreComponent
    
    # Raw analysis results for detailed breakdown
    skill_analysis: Optional[SkillAnalysisResult] = None
    parsed_resume: Optional[ParsedResume] = None
    
    @property
    def final_score(self) -> float:
        """Calculate weighted final score (0-1)."""
        return (
            self.skill_coverage.weighted_score +
            self.semantic_similarity.weighted_score +
            self.evidence_strength.weighted_score +
            self.impact_quality.weighted_score
        )
    
    @property
    def final_percentage(self) -> int:
        """Final score as percentage (0-100)."""
        return int(round(self.final_score * 100))
    
    @property
    def final_level(self) -> ScoreLevel:
        """Get overall score level."""
        score = self.final_score
        if score >= 0.8:
            return ScoreLevel.EXCELLENT
        elif score >= 0.6:
            return ScoreLevel.GOOD
        elif score >= 0.4:
            return ScoreLevel.MODERATE
        elif score >= 0.2:
            return ScoreLevel.NEEDS_WORK
        else:
            return ScoreLevel.POOR
    
    @property
    def all_components(self) -> list[ScoreComponent]:
        """Get all score components."""
        return [
            self.skill_coverage,
            self.semantic_similarity,
            self.evidence_strength,
            self.impact_quality
        ]
    
    @property
    def all_suggestions(self) -> list[str]:
        """Get all improvement suggestions."""
        suggestions = []
        for component in self.all_components:
            suggestions.extend(component.suggestions)
        return suggestions
    
    @property
    def top_suggestions(self) -> list[str]:
        """Get top 5 most impactful suggestions."""
        # Prioritize suggestions from lowest-scoring components
        sorted_components = sorted(self.all_components, key=lambda c: c.score)
        suggestions = []
        for comp in sorted_components:
            for sug in comp.suggestions[:2]:  # Max 2 from each
                if len(suggestions) < 5:
                    suggestions.append(sug)
        return suggestions


def calculate_skill_coverage_score(
    skill_analysis: SkillAnalysisResult
) -> ScoreComponent:
    """
    Calculate skill coverage score.
    Weights must-have skills more heavily than nice-to-have.
    """
    must_have_coverage = skill_analysis.must_have_coverage
    nice_to_have_coverage = skill_analysis.nice_to_have_coverage
    
    # Must-have weighted 70%, nice-to-have 30%
    score = must_have_coverage * 0.7 + nice_to_have_coverage * 0.3
    
    # Generate suggestions
    suggestions = []
    if skill_analysis.must_have_missing:
        missing_critical = skill_analysis.must_have_missing[:3]
        suggestions.append(
            f"Add critical skills: {', '.join(s.replace('_', ' ').title() for s in missing_critical)}"
        )
    
    if skill_analysis.nice_to_have_missing and must_have_coverage > 0.7:
        missing_bonus = skill_analysis.nice_to_have_missing[:2]
        suggestions.append(
            f"Consider adding: {', '.join(s.replace('_', ' ').title() for s in missing_bonus)}"
        )
    
    # Detail string
    details = (
        f"Must-have: {int(must_have_coverage * 100)}% "
        f"({len(skill_analysis.must_have_matched)}/{len(skill_analysis.must_have_matched) + len(skill_analysis.must_have_missing)}) | "
        f"Nice-to-have: {int(nice_to_have_coverage * 100)}% "
        f"({len(skill_analysis.nice_to_have_matched)}/{len(skill_analysis.nice_to_have_matched) + len(skill_analysis.nice_to_have_missing)})"
    )
    
    return ScoreComponent(
        name="Skill Coverage",
        score=score,
        weight=0.4,  # 40% of final score
        details=details,
        suggestions=suggestions
    )


def calculate_semantic_score(
    resume_text: str,
    jd_text: str,
    parsed_resume: Optional[ParsedResume] = None
) -> ScoreComponent:
    """
    Calculate semantic similarity score.
    Uses section-aware similarity if parsed resume available.
    """
    try:
        if parsed_resume:
            # Section-aware scoring
            sections_dict = {
                s.section_type.value: s.content 
                for s in parsed_resume.sections
            }
            result = semantic_similarity_sectioned(sections_dict, jd_text)
            score = result.overall_similarity
            
            # Find best and worst matching sections
            if result.best_matching_sections:
                best_section = result.best_matching_sections[0][0]
                details = f"Best match: {best_section.title()} section"
            else:
                details = "Section analysis completed"
        else:
            score = semantic_similarity(resume_text, jd_text)
            details = "Overall content alignment"
    except Exception as e:
        # Fallback to TF-IDF
        from .scoring import tfidf_similarity
        score = tfidf_similarity(resume_text, jd_text)
        details = "TF-IDF based (embedding unavailable)"
    
    suggestions = []
    if score < 0.5:
        suggestions.append("Use more keywords and terminology from the job description")
    if score < 0.3:
        suggestions.append("Tailor your resume more specifically to this role")
    
    return ScoreComponent(
        name="Semantic Match",
        score=score,
        weight=0.3,  # 30% of final score
        details=details,
        suggestions=suggestions
    )


def calculate_evidence_score(
    skill_analysis: SkillAnalysisResult,
    parsed_resume: Optional[ParsedResume] = None
) -> ScoreComponent:
    """
    Calculate evidence strength score.
    Skills proven in Experience/Projects score higher than just listed.
    """
    if not skill_analysis.detected_skills:
        return ScoreComponent(
            name="Evidence Strength",
            score=0.0,
            weight=0.2,
            details="No skills detected to evaluate",
            suggestions=["Add skills with evidence in projects or experience"]
        )
    
    # Calculate proven vs listed ratio
    proven_count = sum(
        1 for s in skill_analysis.detected_skills.values() 
        if s.is_proven
    )
    listed_only_count = sum(
        1 for s in skill_analysis.detected_skills.values() 
        if s.is_only_listed
    )
    total = len(skill_analysis.detected_skills)
    
    # Score based on proven ratio (proven skills worth more)
    proven_ratio = proven_count / total if total > 0 else 0
    listed_ratio = listed_only_count / total if total > 0 else 0
    
    # Proven skills = full weight, listed = half weight
    score = proven_ratio + (listed_ratio * 0.5)
    score = min(1.0, score)  # Cap at 1.0
    
    details = f"{proven_count} proven in Experience/Projects, {listed_only_count} only listed"
    
    suggestions = []
    if listed_only_count > proven_count:
        # Find skills that are only listed
        listed_skills = [
            s.skill_name for s in skill_analysis.detected_skills.values()
            if s.is_only_listed
        ][:3]
        if listed_skills:
            suggestions.append(
                f"Add project examples using: {', '.join(listed_skills)}"
            )
    
    if proven_count == 0:
        suggestions.append("Add concrete examples in Experience/Projects sections")
    
    return ScoreComponent(
        name="Evidence Strength",
        score=score,
        weight=0.2,  # 20% of final score
        details=details,
        suggestions=suggestions
    )


def calculate_impact_score(
    resume_text: str,
    parsed_resume: Optional[ParsedResume] = None
) -> ScoreComponent:
    """
    Calculate impact quality score.
    Looks for metrics, strong action verbs, and quantified achievements.
    
    Note: This is a simplified version. Full implementation in impact.py
    """
    import re
    
    # Get relevant sections for impact analysis
    if parsed_resume:
        relevant_text = parsed_resume.get_combined_text(
            SectionType.EXPERIENCE,
            SectionType.PROJECTS,
            SectionType.SUMMARY
        )
    else:
        relevant_text = resume_text
    
    text_lower = relevant_text.lower()
    
    # Strong action verbs
    strong_verbs = [
        "built", "developed", "engineered", "designed", "implemented",
        "created", "launched", "deployed", "optimized", "improved",
        "increased", "reduced", "achieved", "led", "managed",
        "architected", "automated", "streamlined", "transformed"
    ]
    
    # Weak verbs
    weak_verbs = [
        "worked on", "helped with", "assisted", "participated",
        "was responsible for", "involved in"
    ]
    
    # Count matches
    strong_count = sum(1 for v in strong_verbs if v in text_lower)
    weak_count = sum(1 for v in weak_verbs if v in text_lower)
    
    # Detect metrics/numbers
    metric_patterns = [
        r'\d+%',  # Percentages
        r'\d+x',  # Multipliers
        r'\$[\d,]+',  # Dollar amounts
        r'\d+\s*(users?|customers?|clients?)',  # User counts
        r'(increased|improved|reduced|decreased)\s+by\s+\d+',  # Quantified improvements
    ]
    
    metric_count = sum(
        len(re.findall(p, relevant_text, re.IGNORECASE))
        for p in metric_patterns
    )
    
    # Calculate score
    verb_score = min(1.0, strong_count / 8)  # Expect ~8 strong verbs
    metric_score = min(1.0, metric_count / 5)  # Expect ~5 metrics
    weak_penalty = min(0.3, weak_count * 0.1)  # Penalty for weak verbs
    
    score = (verb_score * 0.5 + metric_score * 0.5) - weak_penalty
    score = max(0.0, min(1.0, score))
    
    details = f"{strong_count} strong verbs, {metric_count} metrics, {weak_count} weak phrases"
    
    suggestions = []
    if metric_count < 3:
        suggestions.append("Add quantified achievements (%, numbers, timeframes)")
    if strong_count < 5:
        suggestions.append("Use stronger action verbs (built, developed, optimized)")
    if weak_count > 2:
        suggestions.append("Replace weak phrases like 'worked on' with specific actions")
    
    return ScoreComponent(
        name="Impact Quality",
        score=score,
        weight=0.1,  # 10% of final score
        details=details,
        suggestions=suggestions
    )


def compute_hybrid_score(
    resume_text: str,
    jd_text: str,
    role_taxonomy: dict,
    parsed_resume: Optional[ParsedResume] = None
) -> HybridScore:
    """
    Compute complete hybrid score for a resume.
    
    Args:
        resume_text: Full resume text
        jd_text: Job description text
        role_taxonomy: Role taxonomy with must_have/nice_to_have skills
        parsed_resume: Optional pre-parsed resume (will parse if not provided)
        
    Returns:
        HybridScore with all components and final score
    """
    # Parse resume if not provided
    if parsed_resume is None:
        parsed_resume = parse_resume(resume_text)
    
    # Analyze skills with section awareness
    skill_analysis = analyze_skills_sectioned(parsed_resume, role_taxonomy)
    
    # Calculate all score components
    skill_score = calculate_skill_coverage_score(skill_analysis)
    semantic_score = calculate_semantic_score(resume_text, jd_text, parsed_resume)
    evidence_score = calculate_evidence_score(skill_analysis, parsed_resume)
    impact_score = calculate_impact_score(resume_text, parsed_resume)
    
    return HybridScore(
        skill_coverage=skill_score,
        semantic_similarity=semantic_score,
        evidence_strength=evidence_score,
        impact_quality=impact_score,
        skill_analysis=skill_analysis,
        parsed_resume=parsed_resume
    )


def get_score_breakdown_text(hybrid_score: HybridScore) -> str:
    """Generate a text summary of the score breakdown."""
    lines = [
        f"Overall Score: {hybrid_score.final_percentage}/100 ({hybrid_score.final_level.value})",
        "",
        "Score Breakdown:",
    ]
    
    for comp in hybrid_score.all_components:
        lines.append(
            f"  {comp.name}: {comp.percentage}% (weight: {int(comp.weight * 100)}%)"
        )
        lines.append(f"    {comp.details}")
    
    if hybrid_score.top_suggestions:
        lines.append("")
        lines.append("Top Recommendations:")
        for i, sug in enumerate(hybrid_score.top_suggestions, 1):
            lines.append(f"  {i}. {sug}")
    
    return "\n".join(lines)
