"""API server. The Next.js dashboard talks to this.

Runs on your laptop (for prefill access) or can be deployed for read-only queries.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from datetime import datetime
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import requests

from db.models import Job, JobFeedback, Profile, MasterResume, Settings, get_session, init_db
from scraper import load_config

GITHUB_REPO = os.getenv("GITHUB_REPO", "yashpatel2207/job-agent")
GITHUB_WORKFLOW_FILE = os.getenv("GITHUB_WORKFLOW_FILE", "daily-scrape.yml")
GITHUB_REF = os.getenv("GITHUB_REF", "master")

app = FastAPI(title="Job Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/jobs")
def list_jobs(status: str = "new", min_score: float = 0.0):
    session = get_session()
    try:
        q = session.query(Job).filter(Job.score >= min_score)
        if status != "all":
            q = q.filter(Job.status == status)
        q = q.order_by(Job.scraped_at.desc(), Job.score.desc().nullslast())
        return [job_to_dict(j) for j in q.all()]
    finally:
        session.close()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    session = get_session()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(404)
        return job_to_dict(job, full=True)
    finally:
        session.close()


class UpdateJobStatus(BaseModel):
    status: Literal["new", "applied", "skipped"]
    notes: str | None = None


@app.post("/api/jobs/{job_id}/status")
def update_status(job_id: str, payload: UpdateJobStatus):
    session = get_session()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(404)
        job.status = payload.status
        if payload.notes is not None:
            job.user_notes = payload.notes
        if payload.status == "applied":
            job.applied_at = datetime.utcnow()
        elif payload.status == "new":
            job.applied_at = None
        session.commit()
        return {"ok": True}
    finally:
        session.close()


class SaveJobFeedback(BaseModel):
    note: str
    source: Literal["drawer", "skip"] = "drawer"


def _feedback_to_dict(f: JobFeedback) -> dict:
    return {
        "id": f.id,
        "job_id": f.job_id,
        "company": f.company,
        "note": f.note,
        "source": f.source,
        "score_at_time": f.score_at_time,
        "red_flags_at_time": f.red_flags_at_time or [],
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@app.get("/api/jobs/{job_id}/feedback")
def list_job_feedback(job_id: str):
    session = get_session()
    try:
        rows = (
            session.query(JobFeedback)
            .filter(JobFeedback.job_id == job_id)
            .order_by(JobFeedback.created_at.desc())
            .all()
        )
        return [_feedback_to_dict(r) for r in rows]
    finally:
        session.close()


@app.post("/api/jobs/{job_id}/feedback")
def save_job_feedback(job_id: str, payload: SaveJobFeedback):
    note = payload.note.strip()
    if not note:
        raise HTTPException(400, "note is required")
    session = get_session()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(404, "job not found")
        row = JobFeedback(
            job_id=job.id,
            company=job.company,
            note=note,
            source=payload.source,
            score_at_time=job.score,
            red_flags_at_time=job.red_flags or [],
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _feedback_to_dict(row)
    finally:
        session.close()


@app.delete("/api/feedback/{feedback_id}")
def delete_feedback(feedback_id: int):
    session = get_session()
    try:
        row = session.query(JobFeedback).filter(JobFeedback.id == feedback_id).first()
        if not row:
            raise HTTPException(404)
        session.delete(row)
        session.commit()
        return {"ok": True}
    finally:
        session.close()


class CompanyNoteField(BaseModel):
    question: str
    answer: str


class SaveCompanyNotes(BaseModel):
    fields: list[CompanyNoteField]


def _company_key(company: str) -> str:
    return company.strip().lower()


@app.get("/api/company-notes/{company}")
def get_company_notes(company: str):
    key = _company_key(company)
    if not key:
        raise HTTPException(400, "Company name is required")
    session = get_session()
    try:
        p = session.query(Profile).first()
        notes = ((p.data if p else None) or {}).get("company_notes", {}).get(key)
        if not notes:
            return {"company": key, "fields": [], "updated_at": None}
        return {
            "company": key,
            "fields": notes.get("fields", []),
            "updated_at": notes.get("updated_at"),
        }
    finally:
        session.close()


@app.put("/api/company-notes/{company}")
def put_company_notes(company: str, payload: SaveCompanyNotes):
    key = _company_key(company)
    if not key:
        raise HTTPException(400, "Company name is required")
    session = get_session()
    try:
        p = session.query(Profile).first()
        if p is None:
            p = Profile(id=1, data={})
            session.add(p)
            session.flush()
        # Reassign p.data wholesale — SQLAlchemy's plain JSON column
        # doesn't track in-place mutations of nested dicts.
        data = dict(p.data or {})
        notes_root = dict(data.get("company_notes") or {})
        existing = notes_root.get(key) or {}
        record = {
            "display_name": existing.get("display_name") or company.strip(),
            "fields": [{"question": f.question, "answer": f.answer} for f in payload.fields],
            "updated_at": datetime.utcnow().isoformat(),
        }
        notes_root[key] = record
        data["company_notes"] = notes_root
        p.data = data
        session.commit()
        return {"company": key, "fields": record["fields"], "updated_at": record["updated_at"]}
    finally:
        session.close()


def _gh_headers():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise HTTPException(500, "GITHUB_TOKEN not set in backend env")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _is_paused() -> bool:
    s = get_session()
    try:
        row = s.query(Settings).filter(Settings.key == "pipeline_paused").first()
        return bool(row and row.value == "true")
    finally:
        s.close()


def _set_paused(paused: bool):
    s = get_session()
    try:
        row = s.query(Settings).filter(Settings.key == "pipeline_paused").first()
        if row:
            row.value = "true" if paused else "false"
        else:
            s.add(Settings(key="pipeline_paused", value="true" if paused else "false"))
        s.commit()
    finally:
        s.close()


@app.get("/api/cron/status")
def cron_status():
    """Returns pause state plus recent run info from GitHub."""
    paused = _is_paused()
    runs = []
    gh_error: str | None = None
    try:
        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW_FILE}/runs",
            headers=_gh_headers(),
            params={"per_page": 5},
            timeout=10,
        )
        if r.ok:
            for run in r.json().get("workflow_runs", []):
                runs.append({
                    "id": run["id"],
                    "status": run["status"],
                    "conclusion": run["conclusion"],
                    "event": run["event"],
                    "created_at": run["created_at"],
                    "updated_at": run["updated_at"],
                    "html_url": run["html_url"],
                })
        else:
            gh_error = f"GitHub API {r.status_code}: {r.text[:120]}"
    except requests.RequestException as e:
        gh_error = f"GitHub API request failed: {e}"
    except HTTPException as e:
        gh_error = e.detail
    in_progress = next((r for r in runs if r["status"] in ("in_progress", "queued", "waiting")), None)
    last_completed = next((r for r in runs if r["status"] == "completed"), None)
    return {
        "paused": paused,
        "in_progress": in_progress,
        "last_run": last_completed,
        "recent_runs": runs,
        "gh_error": gh_error,
    }


@app.post("/api/cron/trigger")
def cron_trigger():
    """Fire a manual workflow_dispatch run (bypasses pause flag)."""
    r = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW_FILE}/dispatches",
        headers=_gh_headers(),
        json={"ref": GITHUB_REF},
        timeout=10,
    )
    if not r.ok:
        raise HTTPException(r.status_code, f"GitHub API: {r.text[:200]}")
    return {"ok": True, "message": "Run queued. Refresh in a few seconds."}


class PauseToggle(BaseModel):
    paused: bool


@app.post("/api/cron/pause")
def cron_pause(payload: PauseToggle):
    _set_paused(payload.paused)
    return {"ok": True, "paused": payload.paused}


def _derive_careers_url(c: dict) -> str | None:
    ats = c.get("ats")
    slug = c.get("slug")
    if ats == "greenhouse" and slug:
        return f"https://job-boards.greenhouse.io/{slug}"
    if ats == "lever" and slug:
        return f"https://jobs.lever.co/{slug}"
    if ats == "ashby" and slug:
        return f"https://jobs.ashbyhq.com/{slug}"
    if ats == "workday":
        tenant, wd_num, site = c.get("tenant"), c.get("wd_num"), c.get("site")
        if tenant and wd_num and site:
            return f"https://{tenant}.wd{wd_num}.myworkdayjobs.com/{site}"
    return None


@app.get("/api/companies")
def list_companies():
    cfg = load_config()
    return [
        {
            "name": c["name"],
            "careers_url": c.get("careers_url") or _derive_careers_url(c),
        }
        for c in cfg.get("companies", [])
    ]


@app.get("/api/stats")
def stats():
    session = get_session()
    try:
        total = session.query(Job).count()
        new = session.query(Job).filter(Job.status == "new").count()
        applied = session.query(Job).filter(Job.status == "applied").count()
        ready = session.query(Job).filter(Job.status == "new", Job.score >= 7.0).count()
        avg_score_rows = session.query(Job.score).filter(Job.score.isnot(None), Job.status == "new").all()
        avg = sum(r[0] for r in avg_score_rows) / len(avg_score_rows) if avg_score_rows else 0
        return {
            "total": total,
            "new": new,
            "ready_to_review": ready,
            "applied": applied,
            "avg_score": round(avg, 1),
        }
    finally:
        session.close()


def job_to_dict(job: Job, full: bool = False) -> dict:
    d = {
        "id": job.id,
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "apply_url": job.apply_url,
        "ats": job.ats,
        "score": job.score,
        "score_reasons": job.score_reasons or [],
        "red_flags": job.red_flags or [],
        "role_type": job.role_type,
        "status": job.status,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
    }
    if full:
        d["jd_text"] = job.jd_text
        d["user_notes"] = job.user_notes
    return d
