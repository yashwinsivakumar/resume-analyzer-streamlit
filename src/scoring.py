"""
Scoring Module

Provides both TF-IDF (legacy) and semantic similarity scoring.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def tfidf_similarity(resume_text: str, jd_text: str) -> float:
    """Return cosine similarity (0..1) between resume and job description using TF-IDF."""
    vect = TfidfVectorizer(stop_words="english")
    X = vect.fit_transform([resume_text, jd_text])
    return float(cosine_similarity(X[0], X[1])[0][0])


def get_tfidf_keywords(text: str, top_n: int = 20) -> list[tuple[str, float]]:
    """
    Extract top keywords from text using TF-IDF.
    
    Args:
        text: Input text
        top_n: Number of top keywords to return
        
    Returns:
        List of (keyword, score) tuples
    """
    vect = TfidfVectorizer(stop_words="english", max_features=100)
    tfidf_matrix = vect.fit_transform([text])
    feature_names = vect.get_feature_names_out()
    scores = tfidf_matrix.toarray()[0]
    
    # Sort by score
    keyword_scores = list(zip(feature_names, scores))
    keyword_scores.sort(key=lambda x: x[1], reverse=True)
    
    return keyword_scores[:top_n]


def keyword_overlap(resume_text: str, jd_text: str) -> dict:
    """
    Calculate keyword overlap between resume and JD.
    
    Returns:
        Dict with matched, missing, and extra keywords
    """
    resume_keywords = set(kw for kw, _ in get_tfidf_keywords(resume_text, 30))
    jd_keywords = set(kw for kw, _ in get_tfidf_keywords(jd_text, 30))
    
    return {
        "matched": sorted(resume_keywords & jd_keywords),
        "missing": sorted(jd_keywords - resume_keywords),
        "extra": sorted(resume_keywords - jd_keywords),
        "overlap_ratio": len(resume_keywords & jd_keywords) / len(jd_keywords) if jd_keywords else 0
    }
