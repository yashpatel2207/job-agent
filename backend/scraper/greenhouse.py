"""Greenhouse: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"""
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from .base import ScrapedJob


def scrape(company_name: str, slug: str) -> list[ScrapedJob]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  greenhouse {slug}: {e}")
        return []

    jobs = []
    for j in resp.json().get("jobs", []):
        content_html = j.get("content", "")
        jd_text = BeautifulSoup(content_html, "html.parser").get_text("\n", strip=True)

        location = ""
        if j.get("location") and j["location"].get("name"):
            location = j["location"]["name"]

        posted_at = None
        if j.get("updated_at"):
            try:
                posted_at = datetime.fromisoformat(j["updated_at"].replace("Z", "+00:00"))
            except ValueError:
                pass

        jobs.append(ScrapedJob(
            company=company_name,
            title=j.get("title", ""),
            location=location,
            jd_text=jd_text,
            apply_url=j.get("absolute_url", ""),
            ats="greenhouse",
            posted_at=posted_at,
        ))

    return jobs
