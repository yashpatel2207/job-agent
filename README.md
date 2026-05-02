# Job Agent

A personal job application agent: scrapes target companies daily and scores postings against your criteria so you can review the ranked queue each morning.

## What it does

- Scrapes Greenhouse, Lever, Ashby, and Workday career pages for ~25 companies you configure
- Scores each new job against your criteria using a free-tier LLM
- Surfaces the queue in a Next.js dashboard each morning
- You write your own essay answers in your own voice, tailor your resume yourself, and apply manually

## Stack

- Python 3.11 backend (scrapers, LLM API calls)
- SQLite locally, Postgres in production (Supabase or Neon free tier)
- FastAPI server exposes jobs to the frontend
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

Edit both files with your real info. The `profile.json` holds personal details, work auth, EEO defaults, and saved essay answers. The `master_resume.json` is your full resume — kept in the DB so the dashboard can reference it later if you ever add a tailoring feature back.

### 3. Configure your target companies

Edit `backend/companies.yaml`. Each company needs a `slug` that matches its ATS URL:

- Greenhouse: from `boards.greenhouse.io/<slug>`
- Lever: from `jobs.lever.co/<slug>`
- Ashby: from `jobs.ashbyhq.com/<slug>`
- Workday: needs `tenant`, `wd_num`, and `site` fields

Also set your criteria: target roles, required skills, comp floor, location, and exclusions.

### 4. Get three free LLM API keys

The pipeline round-robins across three free-tier providers (Gemini, Groq, Cerebras) so no single provider's rate limit throttles a run. Each is free to obtain, no credit card:

- **Gemini 2.0 Flash** — sign up at https://aistudio.google.com, create a key.
- **Groq** (Llama 3.3 70B) — sign up at https://console.groq.com, create a key.
- **Cerebras** (Llama 3.3 70B) — sign up at https://cloud.cerebras.ai, create a key.

Export all three:

```bash
export GEMINI_API_KEY=...
export GROQ_API_KEY=...
export CEREBRAS_API_KEY=...
```

### 5. Seed the database and run the pipeline once

```bash
cd backend
python seed.py
python main.py
```

This scrapes all companies and scores new jobs. First run takes 2-3 minutes depending on how many roles match.

### 6. Start the local API and dashboard

Shortcut (starts both, Ctrl+C stops both) — run once at the repo root:

```bash
npm install
npm run dev
```

Or start them separately:

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
4. Tailor your resume yourself, apply on the company's site
5. Click "Mark as applied" on the detail page (and "Undo" from the Applied tab if you tap it by mistake)

## Deploy

### Database (Supabase or Neon)

Create a free Postgres database. Grab the connection string.

### GitHub Actions

Set these repo secrets:
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `CEREBRAS_API_KEY`
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
  main.py                  pipeline entry: scrape -> score
  seed.py                  load profile + resume into DB
  server.py                FastAPI for the dashboard
  scraper/                 greenhouse, lever, ashby, workday clients
  scorer/                  LLM scoring
  db/models.py             SQLAlchemy models

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
- LLM API: $0 (runs entirely on free-tier providers — Gemini, Groq, Cerebras, Mistral, NVIDIA NIM, OpenRouter)
