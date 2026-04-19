"""One-time setup: load profile and master resume from JSON files into DB.

Run after copying profile.example.json -> profile.json and filling it in,
and similarly for master_resume.example.json -> master_resume.json.
"""
import json
from pathlib import Path
from db.models import Profile, MasterResume, get_session, init_db

BASE = Path(__file__).parent


def seed():
    init_db()
    session = get_session()
    try:
        resume_path = BASE / "master_resume.json"
        profile_path = BASE / "profile.json"

        if not resume_path.exists():
            print(f"ERROR: {resume_path} not found. Copy master_resume.example.json and fill in your real data.")
            return
        if not profile_path.exists():
            print(f"ERROR: {profile_path} not found. Copy profile.example.json and fill in your real data.")
            return

        with open(resume_path) as f:
            resume_data = json.load(f)
        with open(profile_path) as f:
            profile_data = json.load(f)

        existing_resume = session.query(MasterResume).first()
        if existing_resume:
            existing_resume.data = resume_data
        else:
            session.add(MasterResume(id=1, data=resume_data))

        existing_profile = session.query(Profile).first()
        if existing_profile:
            existing_profile.data = profile_data
        else:
            session.add(Profile(id=1, data=profile_data))

        session.commit()
        print("Seeded profile + master resume.")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
