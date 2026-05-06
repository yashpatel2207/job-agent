"""Daily distillation step: condense raw user feedback into a small rules block.

Reads every JobFeedback row, asks the LLM to extract <=10 short generalizable
rules, and writes the result to Profile.data['scoring_lessons']. The scorer
reads that block on every call and injects it into the scoring prompt.

Cheap: one LLM call per day, ~5K-in / ~1K-out, well within every free tier.
"""
import json
import time
from datetime import datetime
from db.models import JobFeedback, Profile, get_session
from llm import call_llm

DISTILL_PROMPT = """Below are notes a user left on past job postings, each annotated with the
score the LLM gave at the time and any red flags it surfaced. The user is
correcting or annotating the LLM's judgement.

Your task: distill these notes into AT MOST 10 short, generalizable rules
that the LLM should apply when scoring FUTURE job postings. Drop
company-specific noise; surface patterns. Each rule should read as a
directive ("Downgrade ...", "Boost ...", "Treat ... as a red flag").

NOTES:
{notes_block}

Return STRICTLY valid JSON, no markdown, no preamble:
{{"rules": ["rule 1", "rule 2", ...]}}
"""


def _strip_code_fence(text: str) -> str:
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def _format_notes(rows: list[JobFeedback]) -> str:
    lines = []
    for r in rows:
        score = f"{r.score_at_time:.1f}" if r.score_at_time is not None else "n/a"
        flags = r.red_flags_at_time or []
        flags_str = ", ".join(flags) if flags else "none"
        company = r.company or "unknown"
        lines.append(
            f'- [{company}, scored {score}, red flags: {flags_str}]: "{r.note.strip()}"'
        )
    return "\n".join(lines)


def _save_lessons(rules: list[str], note_count: int):
    session = get_session()
    try:
        p = session.query(Profile).first()
        if p is None:
            p = Profile(id=1, data={})
            session.add(p)
            session.flush()
        data = dict(p.data or {})
        data["scoring_lessons"] = {
            "rules": rules,
            "last_distilled_at": datetime.utcnow().isoformat(),
            "raw_notes_count_at_distill": note_count,
        }
        p.data = data
        session.commit()
    finally:
        session.close()


def get_lessons() -> list[str]:
    """Read the distilled rules from Profile.data. Used by the scorer."""
    session = get_session()
    try:
        p = session.query(Profile).first()
        if not p:
            return []
        return ((p.data or {}).get("scoring_lessons") or {}).get("rules") or []
    finally:
        session.close()


def distill_lessons() -> list[str]:
    """Read all JobFeedback rows, condense to <=10 rules, save to Profile.data."""
    session = get_session()
    try:
        rows = (
            session.query(JobFeedback)
            .order_by(JobFeedback.created_at.desc())
            .all()
        )
    finally:
        session.close()

    if not rows:
        _save_lessons([], 0)
        print("Distill: no feedback rows; cleared scoring_lessons.")
        return []

    notes_block = _format_notes(rows)
    prompt = DISTILL_PROMPT.format(notes_block=notes_block)

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            text = call_llm(prompt, want_json=True)
            break
        except RuntimeError as e:
            last_err = e
            wait = 2 ** attempt
            print(f"  Distill: LLM dispatcher error, retrying in {wait}s...")
            time.sleep(wait)
    else:
        print(f"  Distill: failed after retries ({last_err}). Keeping previous lessons.")
        return get_lessons()

    try:
        parsed = json.loads(_strip_code_fence(text))
        rules = parsed.get("rules") if isinstance(parsed, dict) else None
        if not isinstance(rules, list):
            raise ValueError(f"missing 'rules' array, got {type(rules).__name__}")
        rules = [str(r).strip() for r in rules if str(r).strip()][:10]
    except Exception as e:
        print(f"  Distill: parse failed ({e}). Keeping previous lessons.")
        return get_lessons()

    _save_lessons(rules, len(rows))
    print(f"Distill: condensed {len(rows)} notes into {len(rules)} rules.")
    return rules
