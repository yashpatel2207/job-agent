"""Dispatch scrapers, dedupe against DB, return new jobs only."""
import re
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    new: list[ScrapedJob] = []
    seen: set[str] = set()
    dropped_titles = 0
    for j in jobs:
        if j.apply_url in existing or j.apply_url in seen:
            continue
        if not title_is_relevant(j.title):
            dropped_titles += 1
            continue
        seen.add(j.apply_url)
        new.append(j)
    print(f"New jobs: {len(new)} (dropped {dropped_titles} by title filter)")
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
