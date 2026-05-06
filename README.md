# Job Agent

A personal job application agent: scrapes target companies daily and scores postings against your criteria so you can review the ranked queue each morning.

## What it does

- Scrapes Greenhouse, Lever, Ashby, and Workday career pages for ~275 companies you configure (full list in `backend/companies.yaml`)
- Scores each new job against your criteria using a free-tier LLM, with a regex prescreen first so the LLM only sees plausibly-relevant roles
- Surfaces the queue in a Next.js dashboard each morning
- You write your own essay answers in your own voice, tailor your resume yourself, and apply manually

## Stack

- Python 3.11 backend (scrapers, LLM API calls)
- SQLite locally, Postgres in production (Supabase or Neon free tier)
- FastAPI server exposes jobs to the frontend
- Next.js 14 + Tailwind frontend, deployed to Vercel free tier
- GitHub Actions runs the daily scrape at 10am UTC (6am ET)

## How scoring works

Two stages. First, a cheap regex prescreen drops anything whose title doesn't match the frontend/web/JS-TS filter, anything in your exclusion list, security-clearance roles, no-sponsorship language (when `sponsorship_required: true`), and non-US-only locations. Survivors go through batched LLM scoring (5 jobs per call, round-robined across 6 free providers). Per-job feedback you leave in the dashboard gets distilled daily into a small rules block that's injected into both scoring prompts, so the scorer learns what you actually care about over time.

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

Create `backend/profile.json` and `backend/master_resume.json` by hand — they're free-form JSON columns and there are no template files in the repo. See `Profile.data` and `MasterResume.data` in [backend/db/models.py](backend/db/models.py) for the shape `seed.py` expects. The `profile.json` holds personal details, work auth, and EEO defaults; `master_resume.json` is your full resume.

### 3. Configure your target companies

Edit `backend/companies.yaml`. Each company needs a `slug` that matches its ATS URL:

- Greenhouse: from `boards.greenhouse.io/<slug>`
- Lever: from `jobs.lever.co/<slug>`
- Ashby: from `jobs.ashbyhq.com/<slug>`
- Workday: needs `tenant`, `wd_num`, and `site` fields

Also set your criteria: target roles, required skills, comp floor, location, and exclusions.

### 4. Get six free LLM API keys

The pipeline round-robins across six permanently-free-tier providers so no single provider's rate limit throttles a run. Each is free to obtain, no credit card:

- **Gemini 2.5 Flash-Lite** — sign up at https://aistudio.google.com
- **Groq** (Llama 3.3 70B Versatile) — sign up at https://console.groq.com
- **Cerebras** (gpt-oss-120b) — sign up at https://cloud.cerebras.ai
- **Mistral** (Mistral Large) — sign up at https://console.mistral.ai
- **NVIDIA NIM** (Llama 3.3 70B Instruct) — sign up at https://build.nvidia.com
- **OpenRouter** (Qwen3-Next 80B free) — sign up at https://openrouter.ai

Export all six:

```bash
export GEMINI_API_KEY=...
export GROQ_API_KEY=...
export CEREBRAS_API_KEY=...
export MISTRAL_API_KEY=...
export NVIDIA_API_KEY=...
export OPENROUTER_API_KEY=...
```

Missing keys are silently skipped — the dispatcher only fails when *all* providers are absent or throttled — but with all six the pipeline is far less likely to hit a wall mid-run.

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

> **Note:** `package.json` hard-codes the Windows venv path (`venv\Scripts\uvicorn.exe`) for the backend script. On macOS/Linux, skip the shortcut and use the two-terminal flow below.

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
2. Morning: open the dashboard, review ranked jobs in the queue
3. Click through to each company's apply URL, tailor your resume, and write essays in your own voice
4. Click "Mark as applied" on the job card (and "Undo" from the Applied tab if you tap it by mistake)
5. Use the per-job feedback drawer on each card to record why you skipped or what was off — those notes get distilled daily into rules that get injected into both scoring prompts

You can also pause the daily cron or trigger an on-demand run from the dashboard. Both go through the GitHub Actions API and require a `GITHUB_TOKEN` with `actions:write` scope in `backend/.env`.

## Deploy

### Database (Supabase or Neon)

Create a free Postgres database. Grab the connection string.

### GitHub Actions

Set these repo secrets:
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `CEREBRAS_API_KEY`
- `MISTRAL_API_KEY`
- `NVIDIA_API_KEY`
- `OPENROUTER_API_KEY`
- `DATABASE_URL` (Postgres connection string)
- `PROFILE_JSON` (paste the full content of your profile.json)
- `MASTER_RESUME_JSON` (paste the full content of your master_resume.json)

`GITHUB_TOKEN` is auto-provided to the workflow itself. For the dashboard's pause / "Run now" buttons to work locally, generate a personal access token with `actions:write` scope and put it in `backend/.env` as `GITHUB_TOKEN`.

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
  llm.py                   round-robin dispatcher across 6 free providers
  scraper/                 greenhouse, lever, ashby, workday clients
  scorer/                  prescreen + batched LLM scoring
  db/models.py             SQLAlchemy models

frontend/
  app/
    page.tsx               queue
    applied/page.tsx       history
    profile/page.tsx       profile (read-only)
  components/              JobCard, JobFeedback, SkipFeedbackModal,
                           MatchBadge, StatCard, CronControlPanel,
                           CompanyNotes, FilterSegment, Pagination, TierNav
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
