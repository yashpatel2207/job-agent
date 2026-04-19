"""Lever: https://api.lever.co/v0/postings/{slug}?mode=json"""
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from .base import ScrapedJob


def scrape(company_name: str, slug: str) -> list[ScrapedJob]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  lever {slug}: {e}")
        return []

    jobs = []
    for j in resp.json():
        description = j.get("description", "")
        lists = j.get("lists", [])
        extra = "\n\n".join(
            f"{l.get('text', '')}\n{BeautifulSoup(l.get('content', ''), 'html.parser').get_text(chr(10), strip=True)}"
            for l in lists
        )
        jd_text = BeautifulSoup(description, "html.parser").get_text("\n", strip=True) + "\n\n" + extra

        categories = j.get("categories", {})
        location = categories.get("location", "")

        posted_at = None
        if j.get("createdAt"):
            try:
                posted_at = datetime.fromtimestamp(j["createdAt"] / 1000)
            except (ValueError, TypeError):
                pass

        jobs.append(ScrapedJob(
            company=company_name,
            title=j.get("text", ""),
            location=location,
            jd_text=jd_text,
            apply_url=j.get("hostedUrl", ""),
            ats="lever",
            posted_at=posted_at,
        ))

    return jobs
