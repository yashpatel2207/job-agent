# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Personal job-application agent. A daily cron scrapes ~40 ATS career pages (Greenhouse, Lever, Ashby, Workday), an LLM scores each new posting against the user's criteria, and a Next.js dashboard surfaces the ranked queue. Users apply manually — there is no auto-submit.

## Common commands

Run from the **repo root** (starts both API + dashboard via `concurrently`):
```
npm run dev
```
Note: [package.json](package.json) hard-codes the Windows venv path (`venv\Scripts\uvicorn.exe`). On macOS/Linux start the backend manually with `cd backend && source venv/bin/activate && uvicorn server:app --reload --port 8000`.

Backend (from [backend/](backend/), with venv activated):
```
python main.py            # full pipeline: backup → scrape → score
python seed.py            # load profile.json + master_resume.json into DB
python clean.py --all     # wipe jobs table (keeps profile/resume)
python clean.py --rescore # null score fields so the next run re-scores without re-scraping
```

Frontend (from [frontend/](frontend/)):
```
npm run dev    # next dev (port 3000)
npm run build
npm run lint   # next lint
```

There is no test suite — neither backend nor frontend has any test files or test runner configured. Don't invent one unless asked.

## Architecture

### The pipeline (`backend/main.py`)

`main.py` is the only entry point for scrape+score. Steps: backup SQLite → `init_db()` → check pause flag → `scrape_all()` → `filter_new()` → `save_jobs()` → `score_all_unscored()`. `MANUAL_TRIGGER=1` bypasses the pause flag (set by the GitHub Actions `workflow_dispatch` event).

### Scraping (`backend/scraper/`)

- [scraper/__init__.py](backend/scraper/__init__.py) dispatches per-company scrapers in a 10-worker thread pool, then dedupes by `Job.id` and applies a **hardcoded title filter** (`TITLE_INCLUDE_RE` / `TITLE_EXCLUDE_RE`) tuned for **frontend / web / JS-TS roles only** — backend, ML, mobile, data, security, etc. are excluded at this stage. Editing those regexes changes which postings ever reach the scorer.
- ATS-specific scrapers ([greenhouse.py](backend/scraper/greenhouse.py), [lever.py](backend/scraper/lever.py), [ashby.py](backend/scraper/ashby.py), [workday.py](backend/scraper/workday.py)) each return `list[ScrapedJob]`. Job ID is `sha256(company::title::apply_url)[:16]` — see [base.py](backend/scraper/base.py) — so a renamed posting becomes a new row.
- Per-company config lives in [companies.yaml](backend/companies.yaml) alongside the scoring `criteria` block (target roles, skills, comp floor, locations, exclusions, sponsorship flag). Both are loaded by `load_config()`.

### Scoring (`backend/scorer/__init__.py`)

Two-stage filter:
1. **`prescreen()`** — cheap regex pass that hard-drops jobs (score 0) for: title mismatch, exclusion-list hit, security clearance, no-sponsorship language (when `sponsorship_required: true`), or non-US-only locations. Tagged with a `prescreen-*` red flag.
2. **LLM scoring** — survivors go through `score_jobs_batch()` (5 jobs per LLM call, 4-worker pool). On batch parse / length-mismatch failure it falls back to `score_job()` per row. Scoring prompts live in this file as `BATCH_SCORING_PROMPT` / `SCORING_PROMPT`; tweak guidance there.

### LLM dispatcher (`backend/llm.py`)

`call_llm(prompt, want_json=True)` round-robins across **6 permanently-free-tier providers** (Gemini 2.5 Flash-Lite, Groq Llama 3.3 70B Versatile, Cerebras gpt-oss-120b, Mistral Large, NVIDIA NIM Llama 3.3 70B, OpenRouter Qwen3-Next 80B Free). Tracks per-provider daily call counts (UTC midnight reset) and 60s cooldowns on 429s. Full sweep miss → sleep 30s → re-sweep once → raise. **Hard zero-dollar constraint**: only add providers that are permanently free (no trial credits). All providers (except Gemini, which uses `google-genai`) speak the OpenAI chat-completions shape via custom `base_url`.

### API server (`backend/server.py`)

FastAPI. CORS is open to any `localhost:*` origin. Endpoints: `/api/jobs`, `/api/jobs/{id}`, `/api/jobs/{id}/status`, `/api/company-notes/{company}`, `/api/stats`, `/api/cron/{status,trigger,pause}`. The cron endpoints proxy to the GitHub Actions API (requires `GITHUB_TOKEN` with `actions:write`); `pause` toggles a row in the `Settings` table that `main.py` reads at the top of each run. `init_db()` runs on startup — there are no migrations; schema changes go in [db/models.py](backend/db/models.py) and apply on next boot.

### Frontend (`frontend/`)

Next.js 14 App Router + Tailwind. Two routes: queue ([app/page.tsx](frontend/app/page.tsx)) and applied history ([app/applied/page.tsx](frontend/app/applied/page.tsx)). All backend access goes through [lib/api.ts](frontend/lib/api.ts) — `NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000`.

### Daily cron (`.github/workflows/daily-scrape.yml`)

Cron `0 10 * * *` (10am UTC / 6am ET) plus `workflow_dispatch`. Hydrates `profile.json` / `master_resume.json` from secrets (since they're gitignored), runs `seed.py` then `main.py`. Manual dispatches set `MANUAL_TRIGGER=1` to override the pause flag.

## Things to know before editing

- **Schema changes have no migration tool.** Edit [db/models.py](backend/db/models.py); local dev recreates via `init_db()`. For Postgres production you'll need to apply changes by hand or wipe.
- **`profile.json` and `master_resume.json` are gitignored** and required for `seed.py` to run. The README references `profile.example.json` / `master_resume.example.json` but those template files are not currently in the repo — if a fresh setup is needed, scaffold them from [db/models.py](backend/db/models.py) (`Profile.data` / `MasterResume.data` are free-form JSON columns).
- **`backend/tailor/` and `backend/prefill/` are dead code** as of commit `a279e65` ("drop auto-tailoring + prefill button"). `tailor/` is empty save for `__pycache__`; `prefill/__init__.py` is no longer imported anywhere. Don't extend them — confirm with the user first if a feature seems to belong there.
- **Database file** is `backend/job_agent.db` (SQLite, ~70 MB). `main.py` keeps the last 14 timestamped backups in `backend/backups/`. Production uses Postgres via `DATABASE_URL`; the SQLAlchemy models are identical for both.
- **Title filter is the gatekeeper.** A new posting that doesn't match `TITLE_INCLUDE_RE` and miss `TITLE_EXCLUDE_RE` in [scraper/__init__.py](backend/scraper/__init__.py) is dropped before scoring and never appears in the dashboard. If the user reports "X role didn't show up," check that regex first.
- **Required env keys** for a full run: `GEMINI_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`. Missing keys are silently skipped (provider treated as ineligible) — the dispatcher only fails when *all* configured providers are throttled or absent. `GITHUB_TOKEN` is needed only for the dashboard's "Run now" / pause controls.
- **Debugging the LLM dispatcher**: set `LLM_DEBUG=1` to log which provider served each call and which ones failed.
