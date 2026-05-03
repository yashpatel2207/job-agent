"""One-shot migration: add Job.role_type column + index to Postgres.

Run once after pulling the role_type changes:
    cd backend && venv\\Scripts\\python.exe migrate_add_role_type.py
Idempotent — safe to run multiple times.
"""
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text
from db.models import engine

DDL = [
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS role_type VARCHAR",
    "CREATE INDEX IF NOT EXISTS ix_jobs_role_type ON jobs(role_type)",
]


def main():
    with engine.begin() as conn:
        for stmt in DDL:
            print(f"-> {stmt}")
            conn.execute(text(stmt))
    print("done")


if __name__ == "__main__":
    main()
