"""Wipe job data without losing seeded profile / master resume.

Usage:
    python clean.py --all       delete every row in jobs
    python clean.py --rescore   null out score fields so the next pipeline run
                                re-scores everything without re-scraping
"""
import argparse
import sys

from db.models import Job, get_session


def _confirm(msg: str) -> bool:
    return input(f"{msg} [y/N] ").strip().lower() == "y"


def wipe_all():
    session = get_session()
    try:
        n = session.query(Job).count()
        if n == 0:
            print("jobs table is already empty.")
            return
        if not _confirm(f"Delete all {n} job rows?"):
            print("aborted.")
            return
        session.query(Job).delete()
        session.commit()
        print(f"deleted {n} jobs.")
    finally:
        session.close()


def reset_scores():
    session = get_session()
    try:
        n = session.query(Job).filter(Job.score.isnot(None)).count()
        if n == 0:
            print("no scored jobs to reset.")
            return
        if not _confirm(
            f"Reset score fields on {n} jobs (keeps the rows so no re-scrape)?"
        ):
            print("aborted.")
            return
        session.query(Job).update(
            {
                Job.score: None,
                Job.score_reasons: None,
                Job.red_flags: None,
            },
            synchronize_session=False,
        )
        session.commit()
        print(f"reset {n} jobs.")
    finally:
        session.close()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="delete every row in jobs")
    g.add_argument("--rescore", action="store_true", help="null out score fields")
    args = p.parse_args()

    if args.all:
        wipe_all()
    elif args.rescore:
        reset_scores()


if __name__ == "__main__":
    sys.exit(main())
