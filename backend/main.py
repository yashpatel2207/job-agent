"""Daily pipeline. Run this via cron or GitHub Actions.

Steps:
  0. Backup the DB (local SQLite only)
  1. Scrape all configured companies
  2. Dedupe, save new jobs
  3. Score unscored jobs with Claude
"""
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from db.models import Settings, get_session, init_db
from scraper import scrape_all, filter_new, save_jobs
from scorer import score_all_unscored


def is_paused() -> bool:
    """Pause flag only blocks scheduled runs; manual triggers always proceed."""
    if os.environ.get("MANUAL_TRIGGER"):
        return False
    s = get_session()
    try:
        row = s.query(Settings).filter(Settings.key == "pipeline_paused").first()
        return bool(row and row.value == "true")
    finally:
        s.close()


def backup_db():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./job_agent.db")
    if not db_url.startswith("sqlite"):
        return
    db_path = Path(db_url.replace("sqlite:///", ""))
    if not db_path.exists():
        return
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(db_path, backup_dir / f"job_agent_{stamp}.db")

    backups = sorted(backup_dir.glob("job_agent_*.db"))
    for old in backups[:-14]:
        old.unlink()


def main():
    print("=" * 60)
    print("Job Agent Pipeline")
    print("=" * 60)

    backup_db()
    init_db()

    if is_paused():
        print("\nPipeline is paused. Skipping scheduled run.")
        print("Use 'Run now' from the dashboard to override.")
        return 0

    print("\n[1/2] Scraping...")
    scraped = scrape_all()
    new_jobs = filter_new(scraped)
    save_jobs(new_jobs)

    print("\n[2/2] Scoring...")
    score_all_unscored()

    print("\nDone. Open the dashboard to review.")


if __name__ == "__main__":
    sys.exit(main())
