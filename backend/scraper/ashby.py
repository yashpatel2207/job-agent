"""Ashby: https://api.ashbyhq.com/posting-api/job-board/{slug}"""
import requests
from datetime import datetime
from .base import ScrapedJob


def scrape(company_name: str, slug: str) -> list[ScrapedJob]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  ashby {slug}: {e}")
        return []

    jobs = []
    for j in resp.json().get("jobs", []):
        location = j.get("locationName", "")
        if j.get("isRemote"):
            location = f"Remote · {location}" if location else "Remote"

        posted_at = None
        if j.get("publishedAt"):
            try:
                posted_at = datetime.fromisoformat(j["publishedAt"].replace("Z", "+00:00"))
            except ValueError:
                pass

        jobs.append(ScrapedJob(
            company=company_name,
            title=j.get("title", ""),
            location=location,
            jd_text=j.get("descriptionPlain", "") or j.get("descriptionHtml", ""),
            apply_url=j.get("jobUrl", "") or j.get("applyUrl", ""),
            ats="ashby",
            posted_at=posted_at,
        ))

    return jobs
