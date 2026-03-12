"""Embedding Ranker — Stage 2 of the pipeline.

Uses sentence-transformers to compute semantic similarity between
a Job Description and each resume, returning a ranked shortlist.
"""
import numpy as np
from typing import List
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL, TOP_N_SHORTLIST

# Lazy-load model (loaded once, reused across requests)
_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[INFO] Loading embedding model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
        print("[INFO] Embedding model loaded.")
    return _model


def rank_by_embeddings(
    job_description: str,
    resumes: List[dict],
    top_n: int = TOP_N_SHORTLIST,
) -> List[dict]:
    """
    Rank resumes by cosine similarity to the job description.

    Args:
        job_description: The JD text.
        resumes: List of {"filename": str, "text": str}.
        top_n: Number of top candidates to return.

    Returns:
        Sorted list of resumes with added "embedding_score" field.
    """
    model = _get_model()

    # Encode JD
    jd_embedding = model.encode([job_description], show_progress_bar=False)

    # Encode all resumes (batched for efficiency)
    resume_texts = [r["text"][:2000] for r in resumes]  # Truncate for speed
    resume_embeddings = model.encode(resume_texts, show_progress_bar=False, batch_size=32)

    # Compute cosine similarity
    similarities = cosine_similarity(jd_embedding, resume_embeddings)[0]

    # Attach scores
    for i, resume in enumerate(resumes):
        resume["embedding_score"] = round(float(similarities[i]), 4)

    # Sort descending
    ranked = sorted(resumes, key=lambda r: r["embedding_score"], reverse=True)

    # Return top N
    return ranked[:top_n], ranked
