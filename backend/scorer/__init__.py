"""Score jobs against user criteria using Claude."""
import os
import json
import time
from anthropic import Anthropic, APIStatusError, APIConnectionError
from db.models import Job, get_session
from scraper import load_config

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-opus-4-7"

SCORING_PROMPT = """You are evaluating a job posting for a candidate with these criteria:

Target roles: {target_roles}
Required skills: {required_skills}
Preferred skills: {preferred_skills}
Minimum comp: ${comp_min:,}
Acceptable locations: {locations}
Hard exclusions (do NOT apply): {exclude}

Job posting:
Company: {company}
Title: {title}
Location: {location}
---
{jd_text}
---

Return a JSON object with this exact shape, no markdown, no preamble:
{{
  "score": <float 0-10>,
  "reasons": [<2-4 short strings, why it matches>],
  "red_flags": [<0-3 short strings, concerns>],
  "seniority_fit": "below" | "match" | "above",
  "comp_visible": <true if comp is stated in JD, false otherwise>,
  "comp_range": "<string or null>"
}}

Scoring guidance:
- 9-10: Dream fit. Senior/staff level, required skills explicit, comp clearly in range, no red flags.
- 7-8: Strong fit with minor gaps.
- 5-6: Borderline, meaningful gaps.
- 0-4: Not worth applying. Wrong level, missing required skills, in exclusion list, or comp clearly below minimum.
- If the role is in the exclusion list (crypto, web3, etc.), score 0.
"""


def score_job(job: Job, criteria: dict) -> dict:
    prompt = SCORING_PROMPT.format(
        target_roles=", ".join(criteria["target_roles"]),
        required_skills=", ".join(criteria["required_skills"]),
        preferred_skills=", ".join(criteria["preferred_skills"]),
        comp_min=criteria["comp_min"],
        locations=", ".join(criteria["location"]),
        exclude=", ".join(criteria["exclude"]),
        company=job.company,
        title=job.title,
        location=job.location or "unspecified",
        jd_text=job.jd_text[:8000],
    )

    last_err = None
    for attempt in range(4):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            break
        except (APIStatusError, APIConnectionError) as e:
            last_err = e
            wait = 2 ** attempt
            print(f"    rate limit / connection error, retrying in {wait}s...")
            time.sleep(wait)
    else:
        raise last_err

    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return json.loads(text)


def score_all_unscored():
    config = load_config()
    criteria = config["criteria"]
    session = get_session()
    try:
        unscored = session.query(Job).filter(Job.score.is_(None)).all()
        print(f"Scoring {len(unscored)} jobs...")

        for job in unscored:
            try:
                result = score_job(job, criteria)
                job.score = result["score"]
                job.score_reasons = result.get("reasons", [])
                job.red_flags = result.get("red_flags", [])
                session.commit()
                print(f"  {job.company} / {job.title}: {job.score}")
            except Exception as e:
                print(f"  FAILED {job.company} / {job.title}: {e}")
                session.rollback()
    finally:
        session.close()
