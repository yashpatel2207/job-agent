"""Tailor the master resume for a specific job, output a DOCX."""
import json
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from db.models import Job, MasterResume, get_session
from llm import call_claude

MODEL = "opus"

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "resumes"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TAILOR_PROMPT = """You are tailoring a candidate's resume for a specific job.

RULES - follow these strictly:
1. SELECT bullets from the master resume. You may lightly reword (≤15% change) but NEVER fabricate experience.
2. REORDER within each role so the most JD-relevant bullets come first.
3. OMIT bullets that aren't relevant, but keep at least 2 per role.
4. Do NOT invent metrics, skills, or projects not present in the master.

Job:
Company: {company}
Title: {title}
JD:
{jd_text}

Master resume:
{master_json}

Return JSON with this exact shape:
{{
  "summary": "<1-2 sentence tailored summary>",
  "experience": [
    {{
      "company": "<from master>",
      "role": "<from master>",
      "dates": "<from master>",
      "bullets": ["<selected/reordered bullet>", ...]
    }}
  ],
  "skills_emphasized": ["<skill>", "<skill>", ...],
  "changes_summary": "<1-2 sentence description of what you changed and why>"
}}
"""


def tailor_resume(job: Job, master: dict) -> dict:
    prompt = TAILOR_PROMPT.format(
        company=job.company,
        title=job.title,
        jd_text=job.jd_text[:6000],
        master_json=json.dumps(master, indent=2),
    )

    text = call_claude(prompt, model=MODEL)
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return json.loads(text)


def render_docx(tailored: dict, master: dict, output_path: Path):
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_run = p.add_run(master["personal"]["name"])
    name_run.bold = True
    name_run.font.size = Pt(18)

    contact = doc.add_paragraph()
    contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_info = master["personal"]
    contact_text = f"{p_info['location']} · {p_info['email']} · {p_info['phone']} · {p_info.get('linkedin', '')} · {p_info.get('github', '')}"
    contact.add_run(contact_text).font.size = Pt(9.5)

    doc.add_paragraph()
    summary_head = doc.add_paragraph()
    summary_head.add_run("SUMMARY").bold = True
    doc.add_paragraph(tailored["summary"])

    exp_head = doc.add_paragraph()
    exp_head.add_run("EXPERIENCE").bold = True

    for role in tailored["experience"]:
        role_p = doc.add_paragraph()
        role_run = role_p.add_run(f"{role['role']} · {role['company']}")
        role_run.bold = True
        role_p.add_run(f"    {role['dates']}")

        for bullet in role["bullets"]:
            b = doc.add_paragraph(bullet, style="List Bullet")
            b.paragraph_format.space_after = Pt(2)

    skills_head = doc.add_paragraph()
    skills_head.add_run("SKILLS").bold = True
    skills_list = master.get("skills", {})
    for cat, items in skills_list.items():
        sp = doc.add_paragraph()
        sp.add_run(f"{cat.title()}: ").bold = True
        sp.add_run(", ".join(items))

    if master.get("education"):
        edu_head = doc.add_paragraph()
        edu_head.add_run("EDUCATION").bold = True
        for edu in master["education"]:
            ep = doc.add_paragraph()
            ep.add_run(f"{edu['degree']}, {edu['school']}").bold = True
            ep.add_run(f"    {edu['dates']}")

    doc.save(output_path)


def tailor_all_pending(min_score: float = 7.0):
    session = get_session()
    try:
        master_row = session.query(MasterResume).first()
        if not master_row:
            print("ERROR: No master resume in DB. Seed it first.")
            return
        master = master_row.data

        pending = session.query(Job).filter(
            Job.score >= min_score,
            Job.resume_docx_path.is_(None),
        ).all()
        print(f"Tailoring {len(pending)} resumes...")

        for job in pending:
            try:
                tailored = tailor_resume(job, master)
                filename = f"{job.company.replace(' ', '_')}_{job.id[:8]}.docx"
                output_path = OUTPUT_DIR / filename
                render_docx(tailored, master, output_path)

                job.tailored_bullets = tailored
                job.resume_docx_path = str(output_path)
                session.commit()
                print(f"  {job.company} / {job.title}: {filename}")
            except Exception as e:
                print(f"  FAILED {job.company} / {job.title}: {e}")
                session.rollback()
    finally:
        session.close()
