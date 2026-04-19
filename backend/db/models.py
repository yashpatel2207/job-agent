"""Database models. SQLite locally, Postgres in production - same schema."""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean, create_engine, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
import os

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    company = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    location = Column(String)
    jd_text = Column(Text, nullable=False)
    apply_url = Column(String, nullable=False)
    ats = Column(String, nullable=False)
    posted_at = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    score = Column(Float)
    score_reasons = Column(JSON)
    red_flags = Column(JSON)

    resume_docx_path = Column(String)
    tailored_bullets = Column(JSON)
    drafted_answers = Column(JSON)

    status = Column(String, default="new", index=True)
    applied_at = Column(DateTime)
    user_notes = Column(Text)


class Profile(Base):
    __tablename__ = "profile"

    id = Column(Integer, primary_key=True, default=1)
    data = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MasterResume(Base):
    __tablename__ = "master_resume"

    id = Column(Integer, primary_key=True, default=1)
    data = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./job_agent.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
