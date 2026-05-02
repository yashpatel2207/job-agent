"""Workday: POST https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs

Expects each company entry to supply: tenant, wd_num, site.
e.g. tenant='acme', wd_num=5, site='External'
"""
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from bs4 import BeautifulSoup
from .base import ScrapedJob

DETAIL_WORKERS = 6
# Hard upper bound per company. Megacorp tenants (Walmart, Target, Cisco) post
# 5k+ jobs on a single Workday board — paginating all of them can hang the
# pipeline for an hour while our title filter drops ~95% as backend/non-frontend.
# 500 covers any plausible frontend cohort and bounds worst-case wall time.
MAX_POSTINGS_PER_COMPANY = 500


def _fetch_detail(session: requests.Session, base: str, site: str, tenant: str,
                  external_path: str, company_name: str) -> ScrapedJob | None:
    detail_url = f"{base}/wday/cxs/{tenant}/{site}{external_path}"
    try:
        d = session.get(detail_url, timeout=15).json()
    except (requests.RequestException, ValueError):
        return None

    info = d.get("jobPostingInfo", {})
    jd_html = info.get("jobDescription", "")
    jd_text = BeautifulSoup(jd_html, "html.parser").get_text("\n", strip=True)

    posted_at = None
    if info.get("postedOn"):
        try:
            posted_at = datetime.fromisoformat(info["postedOn"].replace("Z", "+00:00"))
        except ValueError:
            pass

    return ScrapedJob(
        company=company_name,
        title=info.get("title", ""),
        location=info.get("location", ""),
        jd_text=jd_text,
        apply_url=f"{base}/{site}{external_path}",
        ats="workday",
        posted_at=posted_at,
    )


def scrape(company_name: str, tenant: str, wd_num: int, site: str) -> list[ScrapedJob]:
    base = f"https://{tenant}.wd{wd_num}.myworkdayjobs.com"
    list_url = f"{base}/wday/cxs/{tenant}/{site}/jobs"

    jobs: list[ScrapedJob] = []
    offset = 0

    # Session reuses TCP connections across the dozens of detail GETs we do per
    # tenant — much cheaper than `requests.get()`'s implicit per-call connection.
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

    try:
        while True:
            payload = {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""}
            try:
                resp = session.post(list_url, json=payload, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"  workday {tenant}: {e}")
                break

            data = resp.json()
            postings = data.get("jobPostings", [])
            if not postings:
                break

            paths = [p.get("externalPath", "") for p in postings if p.get("externalPath")]
            with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
                results = pool.map(
                    lambda path: _fetch_detail(session, base, site, tenant, path, company_name),
                    paths,
                )
                jobs.extend(j for j in results if j is not None)

            if len(postings) < 20:
                break
            offset += 20
            if offset >= MAX_POSTINGS_PER_COMPANY:
                print(f"  workday {tenant}: hit MAX_POSTINGS_PER_COMPANY={MAX_POSTINGS_PER_COMPANY}, stopping pagination")
                break
    finally:
        session.close()

    return jobs
