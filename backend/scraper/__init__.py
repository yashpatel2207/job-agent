"""Dispatch scrapers, dedupe against DB, return new jobs only."""
import re
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from . import greenhouse, lever, ashby, workday
from .base import ScrapedJob
from db.models import Job, get_session

SCRAPING_WORKERS = 10

CONFIG_PATH = Path(__file__).parent.parent / "companies.yaml"

TITLE_INCLUDE_RE = re.compile(r"\b(engineer|engineering|developer|swe|programmer|architect)\b", re.I)
TITLE_EXCLUDE_RE = re.compile(
    r"\b(intern|internship|apprentice|new\s*grad|graduate|entry[-\s]level|"
    r"sales|marketing|recruiter|recruiting|customer|support|success|"
    r"analyst|designer|researcher|scientist|"
    r"product\s+manager|program\s+manager|managers?|"
    r"director|vp|head\s+of|chief|counsel|legal|finance|accountant|"
    r"hardware|mechanical|electrical|firmware|asic|rf\s|optical|"
    r"ios|android|mobile|embedded|robotics|controls|"
    r"back[-\s]?end|"
    r"data\s+engineer|data\s+platform|"
    r"ml\s+engineer|machine\s+learning|ai\s+engineer|ai/ml|"
    r"devops|sre|site\s+reliability|"
    r"security\s+engineer|network\s+engineer|systems\s+engineer|"
    r"qa\s+engineer|test\s+engineer|automation\s+engineer|"
    r"solutions?\s+engineer|forward\s+deployed|"
    r"game\s+engineer|graphics\s+engineer|"
    r"compiler\s+engineer|database\s+engineer)\b",
    re.I,
)


def title_is_relevant(title: str) -> bool:
    if not TITLE_INCLUDE_RE.search(title):
        return False
    if TITLE_EXCLUDE_RE.search(title):
        return False
    return True


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _scrape_one(c: dict) -> list[ScrapedJob]:
    ats = c["ats"]
    name = c["name"]
    slug = c.get("slug")
    print(f"Scraping {name} ({ats})...")
    try:
        if ats == "greenhouse":
            return greenhouse.scrape(name, slug)
        if ats == "lever":
            return lever.scrape(name, slug)
        if ats == "ashby":
            return ashby.scrape(name, slug)
        if ats == "workday":
            return workday.scrape(name, c["tenant"], c["wd_num"], c["site"])
        print(f"  unknown ATS: {ats}")
        return []
    except Exception as e:
        print(f"  FAILED scraping {name} ({ats}): {e}")
        return []


def scrape_all() -> list[ScrapedJob]:
    config = load_config()
    all_jobs: list[ScrapedJob] = []

    with ThreadPoolExecutor(max_workers=SCRAPING_WORKERS) as pool:
        futs = [pool.submit(_scrape_one, c) for c in config["companies"]]
        for fut in as_completed(futs):
            all_jobs.extend(fut.result())

    print(f"\nTotal scraped: {len(all_jobs)}")
    return all_jobs


def filter_new(jobs: list[ScrapedJob]) -> list[ScrapedJob]:
    if not jobs:
        return []

    incoming_urls = list({j.apply_url for j in jobs})
    existing: set[str] = set()
    # Chunk to stay well under SQLite's host-parameter limit (999 pre-3.32).
    CHUNK = 500
    session = get_session()
    try:
        for i in range(0, len(incoming_urls), CHUNK):
            rows = session.query(Job.apply_url).filter(
                Job.apply_url.in_(incoming_urls[i:i + CHUNK])
            ).all()
            existing.update(url for (url,) in rows)
    finally:
        session.close()

    criteria = (load_config().get("criteria") or {})
    max_age_days = criteria.get("max_posting_age_days", 30)
    age_cutoff = datetime.utcnow() - timedelta(days=max_age_days)

    new: list[ScrapedJob] = []
    seen: set[str] = set()
    dropped_titles = 0
    dropped_age = 0
    for j in jobs:
        if j.apply_url in existing or j.apply_url in seen:
            continue
        if not title_is_relevant(j.title):
            dropped_titles += 1
            continue
        # posted_at is None when the ATS doesn't expose it — keep, can't tell.
        # Greenhouse/Ashby/Workday return tz-aware UTC; Lever returns tz-naive local. Strip
        # tzinfo so both compare cleanly against a naive cutoff (a few hours of skew is
        # irrelevant against a 30-day window).
        if j.posted_at is not None:
            posted = j.posted_at.replace(tzinfo=None) if j.posted_at.tzinfo else j.posted_at
            if posted < age_cutoff:
                dropped_age += 1
                continue
        seen.add(j.apply_url)
        new.append(j)
    print(f"New jobs: {len(new)} (dropped {dropped_titles} by title, {dropped_age} by age >{max_age_days}d)")
    return new


def save_jobs(jobs: list[ScrapedJob]):
    session = get_session()
    try:
        for j in jobs:
            session.add(Job(
                id=j.id,
                company=j.company,
                title=j.title,
                location=j.location,
                jd_text=j.jd_text,
                apply_url=j.apply_url,
                ats=j.ats,
                posted_at=j.posted_at,
                status="new",
            ))
        session.commit()
    finally:
        session.close()
