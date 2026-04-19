"""API server. The Next.js dashboard talks to this.

Runs on your laptop (for prefill access) or can be deployed for read-only queries.
"""
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from threading import Thread

from db.models import Job, Profile, MasterResume, get_session, init_db
from prefill import prefill

app = FastAPI(title="Job Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
