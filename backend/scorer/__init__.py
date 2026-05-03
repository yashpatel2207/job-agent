"""Score jobs against user criteria using the multi-provider LLM dispatcher."""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from db.models import Job, get_session
from scraper import load_config, TITLE_EXCLUDE_RE, TITLE_INCLUDE_RE
from llm import call_llm

SCORING_WORKERS = 4
BATCH_SIZE = 5

NO_SPONSORSHIP_RE = re.compile(
    r"(no\s+(?:visa\s+)?sponsorship|"
    r"not\s+(?:able\s+to\s+)?sponsor(?:\s+visas?)?|"
    r"do\s+not\s+(?:offer|provide)\s+(?:visa\s+)?sponsorship|"
    r"unable\s+to\s+(?:offer|provide)\s+(?:visa\s+)?sponsorship|"
    r"no\s+visa\s+transfers?|"
    r"must\s+be\s+(?:legally\s+)?authorized\s+to\s+work\s+(?:in\s+the\s+(?:us|united\s+states|u\.s\.)\s+)?without\s+(?:current\s+or\s+future\s+)?(?:visa\s+|employer\s+)?sponsorship|"
    r"authorized\s+to\s+work\s+in\s+the\s+(?:us|united\s+states|u\.s\.)\s+without\s+(?:current\s+or\s+future\s+)?(?:visa\s+|employer\s+)?sponsorship)",
    re.I,
)

CLEARANCE_RE = re.compile(
    r"\b(security\s+clearance|"
    r"(?:active\s+)?(?:ts/sci|top\s+secret|secret\s+clearance)|"
    r"us\s+citizens?(?:hip)?\s+(?:only|required|is\s+required)|"
    r"must\s+be\s+(?:a\s+)?us\s+citizen|"
    r"us\s+person(?:s)?\s+(?:only|required)|"
    r"itar(?:-|\s)?restricted|"
    r"public\s+trust\s+clearance)\b",
    re.I,
)

NON_US_LOCATION_RE = re.compile(
    r"\b(london|manchester|edinburgh|dublin|berlin|munich|hamburg|amsterdam|"
    r"paris|lyon|madrid|barcelona|milan|rome|warsaw|prague|stockholm|"
    r"copenhagen|oslo|helsinki|zurich|geneva|lisbon|athens|"
    r"toronto|vancouver|montreal|ottawa|calgary|"
    r"bengaluru|bangalore|hyderabad|mumbai|delhi|pune|chennai|gurgaon|noida|kolkata|"
    r"tokyo|osaka|kyoto|seoul|singapore|hong\s*kong|shanghai|beijing|shenzhen|taipei|bangkok|"
    r"sydney|melbourne|brisbane|auckland|wellington|"
    r"sao\s*paulo|rio\s*de\s*janeiro|buenos\s*aires|mexico\s*city|bogota|santiago|lima|"
    r"tel\s*aviv|dubai|riyadh|cairo|johannesburg|cape\s*town|lagos|nairobi|"
    r"united\s+kingdom|\buk\b|ireland|germany|france|spain|italy|netherlands|"
    r"switzerland|sweden|norway|denmark|finland|poland|portugal|"
    r"canada|india|japan|south\s+korea|china|taiwan|thailand|vietnam|philippines|indonesia|malaysia|"
    r"australia|new\s+zealand|"
    r"brazil|argentina|mexico|colombia|chile|peru|"
    r"israel|uae|united\s+arab\s+emirates|saudi\s+arabia|egypt|south\s+africa|nigeria|kenya|"
    r"emea|apac|latam|"
    r"remote\s*[-,\s]\s*(?:europe|emea|apac|india|canada|latam|uk|germany))\b",
    re.I,
)

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
  "sponsorship_signal": "explicit_no" | "explicit_yes" | "unclear",
  "role_type": "frontend" | "fullstack" | "other"
}}

Scoring guidance:
- If the role is in the exclusion list (crypto, web3, etc.), score 0.
- FULL-STACK BACKEND STACK: If the role is full-stack, the backend stack must be JavaScript/TypeScript (Node.js, NestJS, Express, Next.js API routes, tRPC). Full-stack roles primarily backed by Python, Java, Go, Ruby, C#, or Rust should score 4 or below with a red flag noting the backend stack mismatch.
- ROLE TYPE: Classify the role as one of:
    - "frontend" — UI / web client / components / design systems / "Frontend Engineer" / "UI Engineer" / "Web Engineer" with no meaningful backend ownership.
    - "fullstack" — JD describes ownership of both client and server (Node.js / Next.js API routes / tRPC / NestJS / Express). Use this for any "Full Stack", "Full-Stack", or "front + back" framing.
    - "other" — slipped through the title filter but isn't really frontend or full-stack.
- SKILL COVERAGE + ROLE TYPE (graduated): Place the score using BOTH role type and how many of the listed skills the JD explicitly names.
    Frontend-only roles:
      - Required skills (JavaScript, TypeScript) named → 8 (Strong fit; meeting the bar is itself strong).
      - Required + 1-2 preferred (React, Angular, Next.js, design systems, performance, Node.js) → 8.5-9.
      - Required + most/all preferred → 9-10 (Dream fit).
    Full-stack JS/TS roles (passed the FULL-STACK BACKEND STACK rule):
      - Required only → 7.
      - Required + 1-2 preferred → 7.5.
      - Required + most/all preferred → 8 (cap — never exceed 8 for full-stack regardless of fit).
    If required skills are only inferred (not explicitly named): drop one tier.
    If wrong seniority level or comp clearly below minimum: drop into 5-6 or below.
- LOCATION: Fully remote US roles are always a location match. Roles in any of the listed metros are a match. If the role is non-US, OR requires onsite/hybrid presence in a US city NOT on the acceptable list (e.g. Minneapolis, Brooklyn Park MN, Detroit, Salt Lake City, Austin if not listed) with no remote option, CAP the score at 3 and add a "location-not-in-list" red flag — strong skills, comp, and seniority do NOT override this cap.
- SPONSORSHIP: If candidate needs sponsorship AND the JD explicitly states "no sponsorship", "must be authorized to work without sponsorship", "no visa transfers", or similar — set sponsorship_signal to "explicit_no" and CAP the score at 3 with a red flag. If the JD is silent on sponsorship, set "unclear" and do not penalize. If the JD explicitly welcomes sponsorship or mentions H1B transfers, set "explicit_yes" and add a small bonus.
- Federal contractor / defense / clearance-required roles almost always require US persons — treat as "explicit_no" for sponsorship purposes.
"""


BATCH_SCORING_PROMPT = """You are evaluating multiple job postings for a candidate with these criteria:

Target roles: {target_roles}
Required skills: {required_skills}
Preferred skills: {preferred_skills}
Minimum comp: ${comp_min:,}
Acceptable locations: {locations}
Hard exclusions (do NOT apply): {exclude}
Candidate needs H1B sponsorship: {sponsorship_required}

Below is a JSON array of job postings. Score EACH ONE independently.

Jobs to score:
{jobs_json}

Return a JSON object with a single key "results" whose value is an array of objects in the SAME ORDER as the input, one per job. Each result object must have this exact shape:
{{
  "id": <integer matching the input job's id>,
  "score": <float 0-10>,
  "reasons": [<2-4 short strings, why it matches>],
  "red_flags": [<0-3 short strings, concerns>],
  "seniority_fit": "below" | "match" | "above",
  "comp_visible": <true if comp is stated in JD, false otherwise>,
  "comp_range": "<string or null>",
  "sponsorship_signal": "explicit_no" | "explicit_yes" | "unclear",
  "role_type": "frontend" | "fullstack" | "other"
}}

Return STRICTLY valid JSON, no markdown, no preamble. The "results" array length must match the input length.

Scoring guidance:
- If the role is in the exclusion list (crypto, web3, etc.), score 0.
- FULL-STACK BACKEND STACK: If the role is full-stack, the backend stack must be JavaScript/TypeScript (Node.js, NestJS, Express, Next.js API routes, tRPC). Full-stack roles primarily backed by Python, Java, Go, Ruby, C#, or Rust should score 4 or below with a red flag noting the backend stack mismatch.
- ROLE TYPE: Classify the role as one of:
    - "frontend" — UI / web client / components / design systems / "Frontend Engineer" / "UI Engineer" / "Web Engineer" with no meaningful backend ownership.
    - "fullstack" — JD describes ownership of both client and server (Node.js / Next.js API routes / tRPC / NestJS / Express). Use this for any "Full Stack", "Full-Stack", or "front + back" framing.
    - "other" — slipped through the title filter but isn't really frontend or full-stack.
- SKILL COVERAGE + ROLE TYPE (graduated): Place the score using BOTH role type and how many of the listed skills the JD explicitly names.
    Frontend-only roles:
      - Required skills (JavaScript, TypeScript) named → 8 (Strong fit; meeting the bar is itself strong).
      - Required + 1-2 preferred (React, Angular, Next.js, design systems, performance, Node.js) → 8.5-9.
      - Required + most/all preferred → 9-10 (Dream fit).
    Full-stack JS/TS roles (passed the FULL-STACK BACKEND STACK rule):
      - Required only → 7.
      - Required + 1-2 preferred → 7.5.
      - Required + most/all preferred → 8 (cap — never exceed 8 for full-stack regardless of fit).
    If required skills are only inferred (not explicitly named): drop one tier.
    If wrong seniority level or comp clearly below minimum: drop into 5-6 or below.
- LOCATION: Fully remote US roles are always a location match. Roles in any of the listed metros are a match. If the role is non-US, OR requires onsite/hybrid presence in a US city NOT on the acceptable list (e.g. Minneapolis, Brooklyn Park MN, Detroit, Salt Lake City, Austin if not listed) with no remote option, CAP the score at 3 and add a "location-not-in-list" red flag — strong skills, comp, and seniority do NOT override this cap.
- SPONSORSHIP: If candidate needs sponsorship AND the JD explicitly states "no sponsorship", "must be authorized to work without sponsorship", "no visa transfers", or similar — set sponsorship_signal to "explicit_no" and CAP the score at 3 with a red flag. If the JD is silent on sponsorship, set "unclear" and do not penalize. If the JD explicitly welcomes sponsorship or mentions H1B transfers, set "explicit_yes" and add a small bonus.
- Federal contractor / defense / clearance-required roles almost always require US persons — treat as "explicit_no" for sponsorship purposes.
"""


def prescreen(job: Job, criteria: dict) -> dict | None:
    """Cheap regex prefilter. Returns a score dict to hard-drop, or None to pass to the LLM."""
    jd = (job.jd_text or "")[:10000]
    title = job.title or ""
    hay = f"{title}\n{jd}"

    if not TITLE_INCLUDE_RE.search(title) or TITLE_EXCLUDE_RE.search(title):
        return {"score": 0.0, "reasons": [], "red_flags": ["prescreen-title"]}

    exclude_terms = [t.strip() for t in criteria.get("exclude", []) if t.strip()]
    if exclude_terms:
        exclude_re = re.compile(
            r"\b(" + "|".join(re.escape(t) for t in exclude_terms) + r")\b", re.I
        )
        if exclude_re.search(hay):
            return {"score": 0.0, "reasons": [], "red_flags": ["prescreen-excluded"]}

    if CLEARANCE_RE.search(hay):
        return {"score": 0.0, "reasons": [], "red_flags": ["prescreen-clearance"]}

    if criteria.get("sponsorship_required") and NO_SPONSORSHIP_RE.search(jd):
        return {"score": 0.0, "reasons": [], "red_flags": ["prescreen-no-sponsorship"]}

    loc = (job.location or "").strip()
    if loc:
        loc_low = loc.lower()
        has_remote = "remote" in loc_low
        target_locs = [t.lower() for t in criteria.get("location", [])]
        has_us_match = any(t in loc_low for t in target_locs)
        if not has_remote and not has_us_match and NON_US_LOCATION_RE.search(loc_low):
            return {"score": 0.0, "reasons": [], "red_flags": ["prescreen-location"]}

    required = [s.strip().lower() for s in criteria.get("required_skills", []) if s.strip()]
    if required and jd:
        jd_low = jd.lower()
        if not any(re.search(r"\b" + re.escape(s) + r"\b", jd_low) for s in required):
            return {"score": 0.0, "reasons": [], "red_flags": ["prescreen-no-skill-match"]}

    return None


def _strip_code_fence(text: str) -> str:
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def score_job(job: Job, criteria: dict) -> dict:
    """Score a single job. Used as fallback when batch scoring fails."""
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
    for attempt in range(3):
        try:
            text = call_llm(prompt, want_json=True)
            break
        except RuntimeError as e:
            last_err = e
            wait = 2 ** attempt
            print(f"    LLM dispatcher error, retrying in {wait}s...")
            time.sleep(wait)
    else:
        raise last_err

    return json.loads(_strip_code_fence(text))


def score_jobs_batch(jobs: list[Job], criteria: dict) -> list[dict]:
    """Score a batch of jobs in a single LLM call. Raises if parse/length validation fails."""
    payload = [
        {
            "id": j.id,
            "company": j.company,
            "title": j.title,
            "location": j.location or "unspecified",
            "jd_text": (j.jd_text or "")[:6000],
        }
        for j in jobs
    ]
    prompt = BATCH_SCORING_PROMPT.format(
        target_roles=", ".join(criteria["target_roles"]),
        required_skills=", ".join(criteria["required_skills"]),
        preferred_skills=", ".join(criteria["preferred_skills"]),
        comp_min=criteria["comp_min"],
        locations=", ".join(criteria["location"]),
        exclude=", ".join(criteria["exclude"]),
        sponsorship_required="yes" if criteria.get("sponsorship_required") else "no",
        jobs_json=json.dumps(payload, ensure_ascii=False),
    )

    last_err = None
    for attempt in range(3):
        try:
            text = call_llm(prompt, want_json=True)
            break
        except RuntimeError as e:
            last_err = e
            wait = 2 ** attempt
            print(f"    LLM dispatcher error, retrying in {wait}s...")
            time.sleep(wait)
    else:
        raise last_err

    parsed = json.loads(_strip_code_fence(text))
    results = parsed.get("results") if isinstance(parsed, dict) else parsed
    if not isinstance(results, list):
        raise ValueError(f"batch response missing results array: {type(results).__name__}")
    if len(results) != len(jobs):
        raise ValueError(f"batch length mismatch: got {len(results)}, expected {len(jobs)}")

    by_id = {r.get("id"): r for r in results if isinstance(r, dict)}
    ordered: list[dict] = []
    for j in jobs:
        r = by_id.get(j.id)
        if r is None:
            raise ValueError(f"batch response missing id={j.id}")
        ordered.append(r)
    return ordered


def _apply_result(job: Job, result: dict):
    job.score = result["score"]
    job.score_reasons = result.get("reasons", [])
    job.red_flags = result.get("red_flags", [])
    job.role_type = result.get("role_type")


def _score_chunk(chunk: list[Job], criteria: dict) -> list[tuple[Job, dict | Exception]]:
    """Try batched scoring; on failure, fall back to per-job scoring. Returns (job, result-or-exc) per job."""
    try:
        results = score_jobs_batch(chunk, criteria)
        return list(zip(chunk, results))
    except Exception as batch_err:
        print(f"    batch failed ({batch_err}), falling back to per-job for {len(chunk)} jobs")
        out: list[tuple[Job, dict | Exception]] = []
        for job in chunk:
            try:
                out.append((job, score_job(job, criteria)))
            except Exception as e:
                out.append((job, e))
        return out


def score_all_unscored():
    config = load_config()
    criteria = config["criteria"]
    session = get_session()
    session.expire_on_commit = False
    try:
        unscored = session.query(Job).filter(Job.score.is_(None)).all()
        prescreen_count = 0
        to_score: list[Job] = []
        for job in unscored:
            pre = prescreen(job, criteria)
            if pre is not None:
                job.score = pre["score"]
                job.score_reasons = pre["reasons"]
                job.red_flags = pre["red_flags"]
                prescreen_count += 1
                tag = pre["red_flags"][0] if pre["red_flags"] else "prescreen"
                print(f"  [prescreen] {job.company} / {job.title}: dropped ({tag})")
                continue
            to_score.append(job)
        session.commit()

        chunks = [to_score[i:i + BATCH_SIZE] for i in range(0, len(to_score), BATCH_SIZE)]
        scored_count = 0
        failed_count = 0
        total = len(to_score)
        with ThreadPoolExecutor(max_workers=SCORING_WORKERS) as pool:
            fut_to_chunk = {pool.submit(_score_chunk, c, criteria): c for c in chunks}
            for fut in as_completed(fut_to_chunk):
                pairs = fut.result()
                for job, result in pairs:
                    if isinstance(result, Exception):
                        print(f"  FAILED {job.company} / {job.title}: {result}")
                        failed_count += 1
                        continue
                    try:
                        _apply_result(job, result)
                        session.commit()
                        scored_count += 1
                        print(
                            f"  [{scored_count}/{total}] {job.company} / {job.title}: "
                            f"{job.score}"
                        )
                    except Exception as e:
                        print(f"  FAILED {job.company} / {job.title}: {e}")
                        failed_count += 1
                        session.rollback()

        print(
            f"Prescreen-dropped {prescreen_count}; scored {scored_count}; failed {failed_count}."
        )
    finally:
        session.close()
