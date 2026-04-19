"""Dispatch scrapers, dedupe against DB, return new jobs only."""
import yaml
from pathlib import Path
from . import greenhouse, lever, ashby, workday
from .base import ScrapedJob
from db.models import Job, get_session

CONFIG_PATH = Path(__file__).parent.parent / "companies.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def scrape_all() -> list[ScrapedJob]:
    config = load_config()
    all_jobs: list[ScrapedJob] = []

    for c in config["companies"]:
        ats = c["ats"]
        name = c["name"]
        slug = c.get("slug")
        print(f"Scraping {name} ({ats})...")

        if ats == "greenhouse":
            all_jobs.extend(greenhouse.scrape(name, slug))
        elif ats == "lever":
            all_jobs.extend(lever.scrape(name, slug))
        elif ats == "ashby":
            all_jobs.extend(ashby.scrape(name, slug))
        elif ats == "workday":
            all_jobs.extend(workday.scrape(name, c["tenant"], c["wd_num"], c["site"]))
        else:
            print(f"  unknown ATS: {ats}")

    print(f"\nTotal scraped: {len(all_jobs)}")
    return all_jobs


def filter_new(jobs: list[ScrapedJob]) -> list[ScrapedJob]:
    session = get_session()
    try:
        existing_ids = {row.id for row in session.query(Job.id).all()}
    finally:
        session.close()

    new = [j for j in jobs if j.id not in existing_ids]
    print(f"New jobs: {len(new)}")
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
