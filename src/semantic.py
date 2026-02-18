"""
Semantic Similarity Engine

Uses sentence embeddings (MiniLM) for meaning-based matching.
Much better than TF-IDF for understanding semantic similarity.

Example:
- "Built ML models" vs "Experience in machine learning"
- TF-IDF: weak match (different words)
- Embeddings: strong match (same meaning)
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional
from functools import lru_cache
import streamlit as st

# Lazy load sentence-transformers for faster startup
_model = None
_model_name = "all-MiniLM-L6-v2"  # Fast, CPU-friendly, good quality


def get_embedding_model():
    """
    Get or initialize the sentence embedding model.
    Uses Streamlit caching to avoid reloading.
    """
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(_model_name)
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
    return _model


@st.cache_resource
def load_cached_model():
    """Load model with Streamlit caching for persistence across reruns."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(_model_name)


def compute_embedding(text: str, use_cache: bool = True) -> np.ndarray:
    """
    Compute embedding vector for a text.
    
    Args:
        text: Input text to embed
        use_cache: Whether to use Streamlit caching
        
    Returns:
        Embedding vector as numpy array
    """
    if use_cache:
        try:
            model = load_cached_model()
        except Exception:
            model = get_embedding_model()
    else:
        model = get_embedding_model()
    
    # Truncate very long texts to avoid memory issues
    max_length = 5000
    if len(text) > max_length:
        text = text[:max_length]
    
    return model.encode(text, convert_to_numpy=True)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Similarity score between 0 and 1
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


@dataclass
class SemanticMatch:
    """Result of semantic similarity analysis."""
    overall_similarity: float
    section_similarities: dict[str, float]
    best_matching_sections: list[tuple[str, float]]
    embedding_computed: bool = True
    
    @property
    def similarity_percentage(self) -> int:
        """Get similarity as percentage (0-100)."""
        return int(round(self.overall_similarity * 100))
    
    @property
    def match_level(self) -> str:
        """Get human-readable match level."""
        score = self.overall_similarity
        if score >= 0.8:
            return "Excellent"
        elif score >= 0.6:
            return "Good"
        elif score >= 0.4:
            return "Moderate"
        elif score >= 0.2:
            return "Weak"
        else:
            return "Poor"


def semantic_similarity(resume_text: str, jd_text: str) -> float:
    """
    Compute semantic similarity between resume and job description.
    
    Args:
        resume_text: Full resume text
        jd_text: Job description text
        
    Returns:
        Similarity score between 0 and 1
    """
    try:
        resume_embedding = compute_embedding(resume_text)
        jd_embedding = compute_embedding(jd_text)
        return cosine_similarity(resume_embedding, jd_embedding)
    except Exception as e:
        print(f"Semantic similarity error: {e}")
        return 0.0


def semantic_similarity_sectioned(
    resume_sections: dict[str, str],
    jd_text: str
) -> SemanticMatch:
    """
    Compute semantic similarity with section-level breakdown.
    
    Args:
        resume_sections: Dict of section_name -> section_content
        jd_text: Job description text
        
    Returns:
        SemanticMatch with overall and per-section scores
    """
    try:
        jd_embedding = compute_embedding(jd_text)
        
        section_similarities = {}
        weighted_sum = 0.0
        total_weight = 0.0
        
        # Section weights for overall score calculation
        section_weights = {
            "experience": 1.0,
            "projects": 0.9,
            "skills": 0.7,
            "education": 0.5,
            "summary": 0.6,
            "certifications": 0.6,
            "other": 0.3,
        }
        
        for section_name, section_content in resume_sections.items():
            if not section_content.strip():
                continue
                
            section_embedding = compute_embedding(section_content)
            sim = cosine_similarity(section_embedding, jd_embedding)
            section_similarities[section_name] = sim
            
            # Get weight for this section
            weight = section_weights.get(section_name.lower(), 0.3)
            weighted_sum += sim * weight
            total_weight += weight
        
        # Calculate weighted overall similarity
        overall = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Sort sections by similarity
        best_sections = sorted(
            section_similarities.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return SemanticMatch(
            overall_similarity=overall,
            section_similarities=section_similarities,
            best_matching_sections=best_sections[:5],
            embedding_computed=True
        )
        
    except Exception as e:
        print(f"Sectioned semantic similarity error: {e}")
        return SemanticMatch(
            overall_similarity=0.0,
            section_similarities={},
            best_matching_sections=[],
            embedding_computed=False
        )


def compute_skill_semantic_match(
    skill_description: str,
    resume_text: str,
    threshold: float = 0.5
) -> tuple[bool, float]:
    """
    Check if a skill concept is semantically present in resume.
    Useful for detecting skills described differently.
    
    Args:
        skill_description: Description of the skill
        resume_text: Resume text to search
        threshold: Minimum similarity to consider a match
        
    Returns:
        (is_match, similarity_score)
    """
    try:
        skill_embedding = compute_embedding(skill_description)
        resume_embedding = compute_embedding(resume_text)
        sim = cosine_similarity(skill_embedding, resume_embedding)
        return sim >= threshold, sim
    except Exception:
        return False, 0.0


def batch_compute_embeddings(texts: list[str]) -> list[np.ndarray]:
    """
    Compute embeddings for multiple texts efficiently.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    try:
        model = load_cached_model()
    except Exception:
        model = get_embedding_model()
    
    # Truncate long texts
    max_length = 5000
    truncated_texts = [t[:max_length] if len(t) > max_length else t for t in texts]
    
    return model.encode(truncated_texts, convert_to_numpy=True)


def find_most_similar_sections(
    query: str,
    sections: dict[str, str],
    top_k: int = 3
) -> list[tuple[str, float]]:
    """
    Find which resume sections are most similar to a query.
    Useful for finding where specific skills/requirements are addressed.
    
    Args:
        query: Search query (e.g., skill name or requirement)
        sections: Dict of section_name -> content
        top_k: Number of top matches to return
        
    Returns:
        List of (section_name, similarity) tuples
    """
    query_embedding = compute_embedding(query)
    
    similarities = []
    for name, content in sections.items():
        if not content.strip():
            continue
        section_embedding = compute_embedding(content)
        sim = cosine_similarity(query_embedding, section_embedding)
        similarities.append((name, sim))
    
    return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]


# ============ Fallback to TF-IDF if embeddings fail ============

def tfidf_fallback(resume_text: str, jd_text: str) -> float:
    """
    TF-IDF based similarity as fallback.
    Used when sentence-transformers is unavailable.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine
    
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform([resume_text, jd_text])
    return float(sklearn_cosine(tfidf_matrix[0], tfidf_matrix[1])[0][0])


def smart_similarity(resume_text: str, jd_text: str) -> tuple[float, str]:
    """
    Compute similarity using best available method.
    Falls back to TF-IDF if embeddings fail.
    
    Returns:
        (similarity_score, method_used)
    """
    try:
        score = semantic_similarity(resume_text, jd_text)
        return score, "semantic"
    except Exception:
        score = tfidf_fallback(resume_text, jd_text)
        return score, "tfidf"
