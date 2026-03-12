"""LLM Evaluator — Stage 3 of the pipeline.

Sends shortlisted resumes to Claude for deep, structured evaluation.
Each call uses the authenticated user's own API key.
"""
import json
from typing import List

import anthropic

from config import CLAUDE_MODEL, SCORING_WEIGHTS


EVAL_PROMPT = """You are an elite technical recruiter and hiring expert. Evaluate this resume against the job description.

## Job Description
{job_description}

## Resume
{resume_text}

## Instructions
Score this candidate on each dimension from 0-100. Be rigorous and precise.
Return ONLY valid JSON (no markdown, no explanation outside JSON):

{{
  "skills_match": <0-100>,
  "experience_relevance": <0-100>,
  "education_fit": <0-100>,
  "achievements": <0-100>,
  "communication_quality": <0-100>,
  "summary": "<2-3 sentence justification of the overall assessment>",
  "key_strengths": ["<strength1>", "<strength2>", "<strength3>"],
  "gaps": ["<gap1>", "<gap2>"]
}}
"""


def evaluate_single(job_description: str, resume: dict, api_key: str) -> dict:
    """Evaluate a single resume against the JD using Claude with user's API key."""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = EVAL_PROMPT.format(
        job_description=job_description,
        resume_text=resume["text"][:4000],
    )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        evaluation = json.loads(raw)

        composite = sum(
            evaluation.get(dim, 0) * weight
            for dim, weight in SCORING_WEIGHTS.items()
        )
        evaluation["composite_score"] = round(composite, 2)
        evaluation["filename"] = resume["filename"]
        evaluation["embedding_score"] = resume.get("embedding_score", 0)

        return evaluation

    except Exception as e:
        print(f"[WARN] LLM evaluation failed for {resume['filename']}: {e}")
        return {
            "filename": resume["filename"],
            "embedding_score": resume.get("embedding_score", 0),
            "composite_score": resume.get("embedding_score", 0) * 100,
            "skills_match": 0,
            "experience_relevance": 0,
            "education_fit": 0,
            "achievements": 0,
            "communication_quality": 0,
            "summary": f"Evaluation failed: {str(e)}",
            "key_strengths": [],
            "gaps": ["Could not evaluate"],
        }


def evaluate_batch(job_description: str, shortlisted: List[dict], api_key: str, progress_callback=None) -> List[dict]:
    """Evaluate all shortlisted resumes using user's API key. Returns sorted by composite score."""
    results = []
    total = len(shortlisted)

    for i, resume in enumerate(shortlisted):
        result = evaluate_single(job_description, resume, api_key)
        results.append(result)
        if progress_callback:
            progress_callback(i + 1, total)

    results.sort(key=lambda r: r["composite_score"], reverse=True)

    for rank, result in enumerate(results, 1):
        result["rank"] = rank

    return results
