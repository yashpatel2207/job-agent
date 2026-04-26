"""API server. The Next.js dashboard talks to this.

Runs on your laptop (for prefill access) or can be deployed for read-only queries.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from threading import Thread

import requests

from db.models import Job, Profile, MasterResume, Settings, get_session, init_db
from prefill import prefill

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
        q = q.order_by(Job.score.desc().nullslast(), Job.scraped_at.desc())
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
    status: str
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
        session.commit()
        return {"ok": True}
    finally:
        session.close()


class SaveAnswers(BaseModel):
    answers: dict


@app.post("/api/jobs/{job_id}/answers")
def save_answers(job_id: str, payload: SaveAnswers):
    session = get_session()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(404)
        job.drafted_answers = payload.answers
        session.commit()
        return {"ok": True}
    finally:
        session.close()


@app.post("/api/jobs/{job_id}/prefill")
def trigger_prefill(job_id: str):
    session = get_session()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(404)

        def _run():
            prefill(
                apply_url=job.apply_url,
                ats=job.ats,
                resume_path=job.resume_docx_path or "",
                drafted_answers=job.drafted_answers,
            )

        Thread(target=_run, daemon=True).start()
        return {"ok": True, "message": "Browser opening..."}
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


@app.get("/api/stats")
def stats():
    session = get_session()
    try:
        total = session.query(Job).count()
        new = session.query(Job).filter(Job.status == "new").count()
        applied = session.query(Job).filter(Job.status == "applied").count()
        ready = session.query(Job).filter(Job.status == "new", Job.score >= 7.0, Job.resume_docx_path.isnot(None)).count()
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
        "status": job.status,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
        "has_resume": bool(job.resume_docx_path),
    }
    if full:
        d["jd_text"] = job.jd_text
        d["tailored_bullets"] = job.tailored_bullets
        d["drafted_answers"] = job.drafted_answers or {}
        d["user_notes"] = job.user_notes
    return d
