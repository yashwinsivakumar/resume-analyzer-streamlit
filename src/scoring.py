from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def tfidf_similarity(resume_text: str, jd_text: str) -> float:
    """Return cosine similarity (0..1) between resume and job description using TF-IDF."""
    vect = TfidfVectorizer(stop_words="english")
    X = vect.fit_transform([resume_text, jd_text])
    return float(cosine_similarity(X[0], X[1])[0][0])
