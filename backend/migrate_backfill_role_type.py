"""One-shot backfill: infer role_type from title for any Job with role_type IS NULL.

Run after migrate_add_role_type.py to populate legacy rows scored before the column
existed. Future jobs: the LLM scorer (backend/scorer/__init__.py:_apply_result) sets
role_type automatically. Idempotent — only touches rows where role_type IS NULL.
"""
from dotenv import load_dotenv

load_dotenv()

import re
from db.models import Job, get_session

RE_FULLSTACK = re.compile(r"\bfull[-\s]?stack\b", re.I)
RE_FRONTEND = re.compile(r"\bfront[-\s]?end\b", re.I)
RE_UI_DEV = re.compile(r"\bu[ix]\s+(engineer|developer)\b", re.I)
RE_WEB_DEV = re.compile(r"\bweb\s+(engineer|developer)\b", re.I)


def infer_role_type(title: str) -> str:
    """Returns 'frontend' | 'fullstack' | 'other' — never None.

    Unmatched titles map to 'other' to mirror the LLM's three-category output, so
    re-runs of this script skip them via the `IS NULL` filter.
    """
    if RE_FULLSTACK.search(title):
        return "fullstack"
    if RE_FRONTEND.search(title):
        return "frontend"
    if RE_UI_DEV.search(title):
        return "frontend"
    if RE_WEB_DEV.search(title):
        return "frontend"
    return "other"


def main():
    s = get_session()
    try:
        rows = s.query(Job).filter(Job.role_type.is_(None)).all()
        counts = {"frontend": 0, "fullstack": 0, "other": 0}
        for j in rows:
            r = infer_role_type(j.title)
            j.role_type = r
            counts[r] += 1
        s.commit()
        print(f"backfilled {sum(counts.values())} rows:")
        for k, v in counts.items():
            print(f"  {k}: {v}")
    finally:
        s.close()


if __name__ == "__main__":
    main()
