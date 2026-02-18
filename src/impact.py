"""
Impact Analysis Module

Analyzes resume for impactful language:
- Strong action verbs vs weak verbs
- Quantified achievements (metrics, percentages, numbers)
- Result-oriented statements
- Technical depth indicators

This helps candidates understand HOW they present their achievements,
not just WHAT they've done.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .sections import ParsedResume, SectionType


class VerbStrength(Enum):
    """Classification of action verb strength."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass
class ActionVerb:
    """Detected action verb with metadata."""
    verb: str
    strength: VerbStrength
    context: str  # Surrounding text snippet
    section: Optional[str] = None
    suggestion: Optional[str] = None  # Suggested replacement for weak verbs


@dataclass
class Metric:
    """Detected quantified achievement."""
    value: str
    metric_type: str  # percentage, number, currency, time
    context: str
    section: Optional[str] = None


@dataclass
class ImpactAnalysis:
    """Complete impact analysis result."""
    strong_verbs: list[ActionVerb]
    moderate_verbs: list[ActionVerb]
    weak_verbs: list[ActionVerb]
    metrics: list[Metric]
    
    # Scores
    verb_score: float  # 0-1
    metric_score: float  # 0-1
    overall_score: float  # 0-1
    
    # Suggestions
    suggestions: list[str]
    
    @property
    def total_strong_verbs(self) -> int:
        return len(self.strong_verbs)
    
    @property
    def total_weak_verbs(self) -> int:
        return len(self.weak_verbs)
    
    @property
    def total_metrics(self) -> int:
        return len(self.metrics)
    
    @property
    def verb_ratio(self) -> float:
        """Ratio of strong to total verbs."""
        total = len(self.strong_verbs) + len(self.moderate_verbs) + len(self.weak_verbs)
        if total == 0:
            return 0.0
        return len(self.strong_verbs) / total
    
    @property
    def impact_level(self) -> str:
        """Human-readable impact level."""
        if self.overall_score >= 0.8:
            return "Excellent"
        elif self.overall_score >= 0.6:
            return "Good"
        elif self.overall_score >= 0.4:
            return "Moderate"
        elif self.overall_score >= 0.2:
            return "Needs Improvement"
        else:
            return "Weak"


# Strong action verbs by category
STRONG_VERBS = {
    "leadership": [
        "led", "managed", "directed", "headed", "supervised",
        "coordinated", "orchestrated", "spearheaded", "championed"
    ],
    "achievement": [
        "achieved", "accomplished", "attained", "exceeded",
        "surpassed", "outperformed", "delivered", "completed"
    ],
    "creation": [
        "built", "created", "designed", "developed", "engineered",
        "established", "founded", "initiated", "launched", "pioneered"
    ],
    "improvement": [
        "improved", "enhanced", "optimized", "streamlined", "accelerated",
        "boosted", "elevated", "strengthened", "transformed", "revamped"
    ],
    "technical": [
        "implemented", "deployed", "architected", "automated",
        "integrated", "configured", "programmed", "coded", "debugged"
    ],
    "analysis": [
        "analyzed", "evaluated", "assessed", "researched",
        "investigated", "identified", "diagnosed", "resolved"
    ],
    "communication": [
        "presented", "communicated", "negotiated", "persuaded",
        "influenced", "collaborated", "partnered"
    ],
    "growth": [
        "increased", "grew", "expanded", "scaled", "maximized",
        "generated", "produced", "drove"
    ],
    "reduction": [
        "reduced", "decreased", "minimized", "eliminated",
        "cut", "saved", "consolidated"
    ]
}

# Moderate verbs - acceptable but not as impactful
MODERATE_VERBS = [
    "supported", "maintained", "handled", "performed", "conducted",
    "processed", "prepared", "organized", "compiled", "documented",
    "monitored", "tracked", "reported", "reviewed", "tested",
    "updated", "modified", "adjusted", "contributed", "utilized"
]

# Weak verbs/phrases to avoid
WEAK_PHRASES = {
    "worked on": "Try: 'developed', 'built', 'implemented'",
    "helped with": "Try: 'collaborated on', 'contributed to', 'supported'",
    "assisted": "Try: 'supported', 'enabled', 'facilitated'",
    "was responsible for": "Try: 'led', 'managed', 'owned'",
    "responsible for": "Try: 'led', 'managed', 'owned'",
    "involved in": "Try: 'contributed to', 'participated in leading'",
    "participated in": "Try: 'contributed to', 'collaborated on'",
    "dealt with": "Try: 'managed', 'resolved', 'handled'",
    "did": "Try: specific action verb like 'created', 'developed'",
    "made": "Try: 'created', 'designed', 'produced'",
    "got": "Try: 'achieved', 'obtained', 'secured'",
    "worked with": "Try: 'collaborated with', 'partnered with'",
    "used": "Try: 'leveraged', 'utilized', 'applied'",
    "learned": "Try: 'mastered', 'acquired expertise in'",
    "tried": "Try: 'attempted', 'tested', 'experimented with'",
}

# Metric patterns
METRIC_PATTERNS = {
    "percentage": r'(\d+(?:\.\d+)?)\s*%',
    "multiplier": r'(\d+(?:\.\d+)?)\s*[xX]\b',
    "currency": r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:K|M|B|million|billion)?',
    "users": r'(\d[\d,]*)\s*(?:users?|customers?|clients?|subscribers?)',
    "time_saved": r'(?:saved?|reduced?)\s*(\d+)\s*(?:hours?|days?|weeks?|months?)',
    "count": r'(\d[\d,]*)\s*(?:projects?|applications?|features?|tickets?|requests?)',
    "improvement": r'(?:by|of)\s*(\d+(?:\.\d+)?)\s*%',
    "accuracy": r'(\d+(?:\.\d+)?)\s*%?\s*(?:accuracy|precision|recall|f1)',
    "latency": r'(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?|seconds?)\s*(?:latency|response)',
    "uptime": r'(\d+(?:\.\d+)?)\s*%?\s*(?:uptime|availability)',
}


def get_all_strong_verbs() -> set[str]:
    """Get flat set of all strong verbs."""
    verbs = set()
    for category_verbs in STRONG_VERBS.values():
        verbs.update(category_verbs)
    return verbs


def find_verbs_in_text(
    text: str,
    section_name: Optional[str] = None
) -> tuple[list[ActionVerb], list[ActionVerb], list[ActionVerb]]:
    """
    Find and classify action verbs in text.
    
    Returns:
        (strong_verbs, moderate_verbs, weak_verbs)
    """
    strong = []
    moderate = []
    weak = []
    
    text_lower = text.lower()
    
    # Find strong verbs
    all_strong = get_all_strong_verbs()
    for verb in all_strong:
        pattern = rf'\b{re.escape(verb)}(?:ed|ing|s)?\b'
        for match in re.finditer(pattern, text_lower):
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            context = text[start:end].strip()
            
            strong.append(ActionVerb(
                verb=verb,
                strength=VerbStrength.STRONG,
                context=f"...{context}...",
                section=section_name
            ))
    
    # Find moderate verbs
    for verb in MODERATE_VERBS:
        pattern = rf'\b{re.escape(verb)}(?:ed|ing|s)?\b'
        for match in re.finditer(pattern, text_lower):
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            context = text[start:end].strip()
            
            moderate.append(ActionVerb(
                verb=verb,
                strength=VerbStrength.MODERATE,
                context=f"...{context}...",
                section=section_name
            ))
    
    # Find weak phrases
    for phrase, suggestion in WEAK_PHRASES.items():
        pattern = rf'\b{re.escape(phrase)}\b'
        for match in re.finditer(pattern, text_lower):
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end].strip()
            
            weak.append(ActionVerb(
                verb=phrase,
                strength=VerbStrength.WEAK,
                context=f"...{context}...",
                section=section_name,
                suggestion=suggestion
            ))
    
    return strong, moderate, weak


def find_metrics_in_text(
    text: str,
    section_name: Optional[str] = None
) -> list[Metric]:
    """Find quantified achievements/metrics in text."""
    metrics = []
    
    for metric_type, pattern in METRIC_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(1) if match.groups() else match.group(0)
            
            # Get context
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()
            
            metrics.append(Metric(
                value=value,
                metric_type=metric_type,
                context=f"...{context}...",
                section=section_name
            ))
    
    return metrics


def analyze_impact(
    text: str,
    parsed_resume: Optional[ParsedResume] = None
) -> ImpactAnalysis:
    """
    Perform complete impact analysis on resume text.
    
    Args:
        text: Full resume text
        parsed_resume: Optional parsed resume for section-aware analysis
        
    Returns:
        ImpactAnalysis with verbs, metrics, scores, and suggestions
    """
    all_strong = []
    all_moderate = []
    all_weak = []
    all_metrics = []
    
    if parsed_resume:
        # Analyze relevant sections
        relevant_sections = [
            SectionType.EXPERIENCE,
            SectionType.PROJECTS,
            SectionType.SUMMARY
        ]
        
        for section in parsed_resume.sections:
            if section.section_type in relevant_sections:
                strong, moderate, weak = find_verbs_in_text(
                    section.content,
                    section.section_type.value
                )
                all_strong.extend(strong)
                all_moderate.extend(moderate)
                all_weak.extend(weak)
                
                metrics = find_metrics_in_text(
                    section.content,
                    section.section_type.value
                )
                all_metrics.extend(metrics)
    else:
        # Analyze full text
        strong, moderate, weak = find_verbs_in_text(text)
        all_strong.extend(strong)
        all_moderate.extend(moderate)
        all_weak.extend(weak)
        
        all_metrics = find_metrics_in_text(text)
    
    # Remove duplicates (same verb found multiple times)
    seen_strong = set()
    unique_strong = []
    for v in all_strong:
        key = (v.verb, v.section)
        if key not in seen_strong:
            seen_strong.add(key)
            unique_strong.append(v)
    
    seen_moderate = set()
    unique_moderate = []
    for v in all_moderate:
        key = (v.verb, v.section)
        if key not in seen_moderate:
            seen_moderate.add(key)
            unique_moderate.append(v)
    
    # Keep all weak phrases (important feedback)
    
    # Calculate scores
    strong_count = len(unique_strong)
    weak_count = len(all_weak)
    metric_count = len(all_metrics)
    
    # Verb score: reward strong, penalize weak
    verb_score = min(1.0, strong_count / 10)  # Expect ~10 strong verbs
    weak_penalty = min(0.4, weak_count * 0.1)  # Penalty for weak
    verb_score = max(0.0, verb_score - weak_penalty)
    
    # Metric score: reward quantified achievements
    metric_score = min(1.0, metric_count / 6)  # Expect ~6 metrics
    
    # Overall score
    overall_score = verb_score * 0.6 + metric_score * 0.4
    
    # Generate suggestions
    suggestions = []
    
    if strong_count < 5:
        suggestions.append(
            f"Add more strong action verbs. Current: {strong_count}, Target: 8+"
        )
    
    if weak_count > 0:
        # Get unique weak phrases
        weak_phrases_found = set(v.verb for v in all_weak)
        for phrase in list(weak_phrases_found)[:3]:
            if phrase in WEAK_PHRASES:
                suggestions.append(f"Replace '{phrase}' - {WEAK_PHRASES[phrase]}")
    
    if metric_count < 3:
        suggestions.append(
            "Add more quantified achievements (percentages, numbers, metrics)"
        )
    
    if metric_count == 0:
        suggestions.append(
            "Include specific results: % improvement, users impacted, time saved"
        )
    
    # Specific metric type suggestions
    metric_types_found = set(m.metric_type for m in all_metrics)
    if "percentage" not in metric_types_found:
        suggestions.append("Add percentage improvements (e.g., 'reduced load time by 40%')")
    if "users" not in metric_types_found and "count" not in metric_types_found:
        suggestions.append("Mention scale/reach (e.g., 'serving 10,000 users')")
    
    return ImpactAnalysis(
        strong_verbs=unique_strong,
        moderate_verbs=unique_moderate,
        weak_verbs=all_weak,
        metrics=all_metrics,
        verb_score=verb_score,
        metric_score=metric_score,
        overall_score=overall_score,
        suggestions=suggestions[:5]  # Top 5 suggestions
    )


def get_verb_suggestions(weak_verbs: list[ActionVerb]) -> list[dict]:
    """Get specific replacement suggestions for weak verbs."""
    suggestions = []
    seen = set()
    
    for verb in weak_verbs:
        if verb.verb not in seen:
            seen.add(verb.verb)
            suggestions.append({
                "original": verb.verb,
                "suggestion": verb.suggestion or WEAK_PHRASES.get(verb.verb, "Use a stronger verb"),
                "context": verb.context
            })
    
    return suggestions


def get_impact_summary(analysis: ImpactAnalysis) -> str:
    """Generate a text summary of impact analysis."""
    lines = [
        f"Impact Score: {int(analysis.overall_score * 100)}/100 ({analysis.impact_level})",
        "",
        f"Strong Verbs: {analysis.total_strong_verbs}",
        f"Weak Phrases: {analysis.total_weak_verbs}",
        f"Quantified Metrics: {analysis.total_metrics}",
    ]
    
    if analysis.suggestions:
        lines.append("")
        lines.append("Suggestions:")
        for i, sug in enumerate(analysis.suggestions, 1):
            lines.append(f"  {i}. {sug}")
    
    return "\n".join(lines)
