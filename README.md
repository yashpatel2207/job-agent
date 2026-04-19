# Job Agent

A personal job application agent: scrapes target companies daily, scores postings against your criteria, generates tailored resumes, and prefills application forms for you to review and submit.

## What it does

- Scrapes Greenhouse, Lever, Ashby, and Workday career pages for ~25 companies you configure
- Scores each new job against your criteria using Claude
- For jobs scoring 7+, generates a tailored DOCX resume (selects and reorders bullets from your master resume, never fabricates)
- Surfaces the queue in a Next.js dashboard each morning
- On approval, opens Chromium with the application form prefilled for final review
- You review, edit essay questions in your own voice, and submit manually

## Stack

- Python 3.11 backend (scrapers, Claude API calls, Playwright)
- SQLite locally, Postgres in production (Supabase or Neon free tier)
- FastAPI server exposes jobs to the frontend and triggers prefill on demand
- Next.js 14 + Tailwind frontend, deployed to Vercel free tier
- GitHub Actions runs the daily scrape at 10am UTC (6am ET)

## First-time setup

Requires **Python 3.11+** and **Node 18.17+** (Next.js 14 minimum).

### 1. Clone and install

```bash
git clone <your-fork>
cd job-agent

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Frontend
cd ../frontend
npm install
```

### 2. Create your profile and master resume

```bash
cd backend
cp profile.example.json profile.json
cp master_resume.example.json master_resume.json
```

Edit both files with your real info. The `profile.json` holds personal details, work auth, EEO defaults, and saved essay answers. The `master_resume.json` is your full resume with every bullet tagged by skill and scope - tailoring selects from this pool.

### 3. Configure your target companies

Edit `backend/companies.yaml`. Each company needs a `slug` that matches its ATS URL:

- Greenhouse: from `boards.greenhouse.io/<slug>`
- Lever: from `jobs.lever.co/<slug>`
- Ashby: from `jobs.ashbyhq.com/<slug>`
- Workday: needs `tenant`, `wd_num`, and `site` fields

Also set your criteria: target roles, required skills, comp floor, location, and exclusions.

### 4. Get an Anthropic API key

Sign up at https://console.anthropic.com, create an API key, and export it:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 5. Seed the database and run the pipeline once

```bash
cd backend
python seed.py
python main.py
```

This scrapes all companies, scores new jobs, and generates tailored resumes. First run takes 5-10 minutes depending on how many roles match.

### 6. Start the local API and dashboard

Terminal 1 (API):
```bash
cd backend
uvicorn server:app --reload --port 8000
```

Terminal 2 (dashboard):
```bash
cd frontend
npm run dev
```

Open http://localhost:3000.

## Daily workflow

1. GitHub Actions runs `main.py` at 6am ET, populates the database
2. Morning: open the dashboard, review ranked jobs
3. For ones you want to apply to, open the detail page and write your custom essay answers in your own voice
4. Start the local API (`uvicorn server:app` in backend folder)
5. Click "Approve and prefill" - Chromium opens with the form filled
6. You scan, tweak, submit
7. Click "Mark as applied" on the detail page

## Deploy

### Database (Supabase or Neon)

Create a free Postgres database. Grab the connection string.

### GitHub Actions

Set these repo secrets:
- `ANTHROPIC_API_KEY`
- `DATABASE_URL` (Postgres connection string)
- `PROFILE_JSON` (paste the full content of your profile.json)
- `MASTER_RESUME_JSON` (paste the full content of your master_resume.json)

### Frontend (Vercel)

Connect the repo to Vercel, set root directory to `frontend/`, add env var:
- `NEXT_PUBLIC_API_URL` = your deployed API URL, OR leave pointing at localhost:8000 if you only use the dashboard locally

For v1, running the frontend locally is simplest. Deploy to Vercel when you want to check the queue from your phone.

## File map

```
backend/
  companies.yaml           target companies + criteria
  profile.json             personal info, EEO, saved answers (gitignored)
  master_resume.json       your full tagged resume (gitignored)
  main.py                  pipeline entry: scrape -> score -> tailor
  seed.py                  load profile + resume into DB
  server.py                FastAPI for the dashboard
  scraper/                 greenhouse, lever, ashby, workday clients
  scorer/                  Claude scoring
  tailor/                  resume tailor + DOCX renderer
  prefill/                 Playwright form fillers per ATS
  db/models.py             SQLAlchemy models
  output/resumes/          generated DOCX files

frontend/
  app/
    page.tsx               queue
    job/[id]/page.tsx      detail + essay editor
    applied/page.tsx       history
    profile/page.tsx       profile (read-only in v1)
  components/              JobCard, MatchBadge, StatCard
  lib/api.ts               backend client

.github/workflows/
  daily-scrape.yml         6am cron
```

## What v1 intentionally does NOT do

- Auto-submit applications. You always review and click submit.
- LinkedIn Easy Apply automation (risks account ban)
- Inline profile editing (JSON file for now)
- Multi-resume profiles
- Response tracking
- Cover letter generation

These are candidates for v2 once you've used v1 for two weeks and know what's actually missing.

## Costs

- Hosting: $0 (GitHub Actions + Vercel + Neon/Supabase free tiers)
- Claude API: ~$3-8/month at 5-10 scored jobs per day plus tailoring
