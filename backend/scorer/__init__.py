"""Score jobs against user criteria using Claude."""
import json
import time
from db.models import Job, get_session
from scraper import load_config
from llm import call_claude

MODEL = "sonnet"

SCORING_PROMPT = """You are evaluating a job posting for a candidate with these criteria:

Target roles: {target_roles}
Required skills: {required_skills}
Preferred skills: {preferred_skills}
Minimum comp: ${comp_min:,}
Acceptable locations: {locations}
Hard exclusions (do NOT apply): {exclude}
Candidate needs H1B sponsorship: {sponsorship_required}

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
  "comp_range": "<string or null>",
  "sponsorship_signal": "explicit_no" | "explicit_yes" | "unclear"
}}

Scoring guidance:
- 9-10: Dream fit. Senior/staff level, required skills explicit, comp clearly in range, no red flags.
- 7-8: Strong fit with minor gaps.
- 5-6: Borderline, meaningful gaps.
- 0-4: Not worth applying. Wrong level, missing required skills, in exclusion list, or comp clearly below minimum.
- If the role is in the exclusion list (crypto, web3, etc.), score 0.
- LOCATION: The acceptable locations list is broad. Treat any US-based role (remote or in any of the listed metros) as a location match. Only penalize for location if the role is non-US, requires being in a city not on the list (e.g. Detroit, Salt Lake City), or requires in-office presence somewhere the candidate cannot relocate to.
- SPONSORSHIP: If candidate needs sponsorship AND the JD explicitly states "no sponsorship", "must be authorized to work without sponsorship", "no visa transfers", or similar — set sponsorship_signal to "explicit_no" and CAP the score at 3 with a red flag. If the JD is silent on sponsorship, set "unclear" and do not penalize. If the JD explicitly welcomes sponsorship or mentions H1B transfers, set "explicit_yes" and add a small bonus.
- Federal contractor / defense / clearance-required roles almost always require US persons — treat as "explicit_no" for sponsorship purposes.
"""


def score_job(job: Job, criteria: dict) -> dict:
    prompt = SCORING_PROMPT.format(
        target_roles=", ".join(criteria["target_roles"]),
        required_skills=", ".join(criteria["required_skills"]),
        preferred_skills=", ".join(criteria["preferred_skills"]),
        comp_min=criteria["comp_min"],
        locations=", ".join(criteria["location"]),
        exclude=", ".join(criteria["exclude"]),
        sponsorship_required="yes" if criteria.get("sponsorship_required") else "no",
        company=job.company,
        title=job.title,
        location=job.location or "unspecified",
        jd_text=job.jd_text[:8000],
    )

    last_err = None
    for attempt in range(4):
        try:
            text = call_claude(prompt, model=MODEL)
            break
        except RuntimeError as e:
            last_err = e
            wait = 2 ** attempt
            print(f"    claude CLI error, retrying in {wait}s...")
            time.sleep(wait)
    else:
        raise last_err

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
        scored_count = 0
        for job in unscored:
            try:
                result = score_job(job, criteria)
                job.score = result["score"]
                job.score_reasons = result.get("reasons", [])
                job.red_flags = result.get("red_flags", [])
                session.commit()
                scored_count += 1
                print(f"  [{scored_count}] {job.company} / {job.title}: {job.score}")
            except Exception as e:
                print(f"  FAILED {job.company} / {job.title}: {e}")
                session.rollback()
        print(f"LLM-scored {scored_count} jobs.")
    finally:
        session.close()