"""
filter.py - Use Claude API to score job relevance against the user's CV.
"""

import json
import logging
import os
from pathlib import Path

import anthropic

from .searcher import Job
from . import tracker

logger = logging.getLogger(__name__)


def _load_cv(cv_path: str) -> str:
    path = Path(cv_path)
    if not path.is_absolute():
        path = Path(__file__).parent.parent / cv_path
    if not path.exists():
        raise FileNotFoundError(f"CV file not found: {path}")
    return path.read_text(encoding="utf-8")


def score_job(client: anthropic.Anthropic, cv_text: str, job: Job) -> tuple[int, str]:
    """
    Ask Claude to score job relevance (0-100) and provide a one-sentence reason.
    Returns (score, reason).
    """
    prompt = f"""You are a career advisor. Given the following CV and job posting, rate how relevant this job is for the candidate.

Base your score on TWO dimensions:
1. CV match – how well the candidate's skills, experience, and background align with the job requirements.
2. Domain relevance – whether the role belongs to the same professional field or closely adjacent fields as the candidate's background, even if the exact skills aren't listed in the CV.

A role that is in the same domain as the candidate (e.g. same industry, same type of work, transferable skills) should score higher than a role in a completely unrelated field, even if the CV doesn't mention every required technology.

CV:
{cv_text}

---

Job Title: {job.title}
Company: {job.company}
Location: {job.location}
Job Description:
{job.description[:3000]}

---

Respond ONLY with valid JSON in this exact format (no extra text):
{{"score": <integer 0-100>, "reason": "<one sentence explanation in Hebrew>"}}

Score 0-100 where:
- 90-100: Excellent match – strong CV alignment and directly in the candidate's domain
- 70-89: Good match – most requirements fit or highly relevant domain with transferable skills
- 50-69: Partial match – adjacent domain or partial skill overlap
- 0-49: Poor match – unrelated field or very few relevant skills
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        data = json.loads(raw)
        score = max(0, min(100, int(data["score"])))
        reason = str(data.get("reason", ""))
        return score, reason
    except Exception as e:
        logger.warning("Claude scoring failed for job %s: %s", job.job_id, e)
        return 0, "שגיאה בניתוח"


def filter_jobs(jobs: list[Job], config: dict) -> list[tuple[Job, int, str]]:
    """
    Score all jobs with Claude and return those above the min_relevance_score threshold.
    Returns list of (job, score, reason) tuples, sorted by score descending.
    """
    filter_cfg = config["filter"]
    min_score: int = filter_cfg.get("min_relevance_score", 70)
    cv_path: str = filter_cfg.get("cv_path", "cv.txt")

    cv_text = _load_cv(cv_path)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    results: list[tuple[Job, int, str]] = []

    for job in jobs:
        if not job.description:
            logger.debug("Skipping %s - no description", job.job_id)
            continue

        if tracker.is_emailed(job.job_id):
            logger.debug("Skipping %s - already emailed", job.job_id)
            continue

        logger.info("Scoring: %s @ %s", job.title, job.company)
        score, reason = score_job(client, cv_text, job)
        logger.info("  → score=%d reason=%s", score, reason)

        if score >= min_score:
            results.append((job, score, reason))

    results.sort(key=lambda x: x[1], reverse=True)
    return results
