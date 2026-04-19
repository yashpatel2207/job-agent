"""Workday: POST https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs

Expects each company entry to supply: tenant, wd_num, site.
e.g. tenant='acme', wd_num=5, site='External'
"""
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from .base import ScrapedJob


def scrape(company_name: str, tenant: str, wd_num: int, site: str) -> list[ScrapedJob]:
    base = f"https://{tenant}.wd{wd_num}.myworkdayjobs.com"
    list_url = f"{base}/wday/cxs/{tenant}/{site}/jobs"

    jobs = []
    offset = 0
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    while True:
        payload = {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""}
        try:
            resp = requests.post(list_url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  workday {tenant}: {e}")
            break

        data = resp.json()
        postings = data.get("jobPostings", [])
        if not postings:
            break

        for p in postings:
            external_path = p.get("externalPath", "")
            detail_url = f"{base}/wday/cxs/{tenant}/{site}{external_path}"

            try:
                d = requests.get(detail_url, headers=headers, timeout=15).json()
            except requests.RequestException:
                continue

            info = d.get("jobPostingInfo", {})
            jd_html = info.get("jobDescription", "")
            jd_text = BeautifulSoup(jd_html, "html.parser").get_text("\n", strip=True)

            apply_url = f"{base}{external_path}"

            posted_at = None
            if info.get("postedOn"):
                try:
                    posted_at = datetime.fromisoformat(info["postedOn"].replace("Z", "+00:00"))
                except ValueError:
                    pass

            jobs.append(ScrapedJob(
                company=company_name,
                title=info.get("title", ""),
                location=info.get("location", ""),
                jd_text=jd_text,
                apply_url=apply_url,
                ats="workday",
                posted_at=posted_at,
            ))

        if len(postings) < 20:
            break
        offset += 20

    return jobs
