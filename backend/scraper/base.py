"""Normalized job shape that all scrapers return."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import hashlib


@dataclass
class ScrapedJob:
    company: str
    title: str
    location: str
    jd_text: str
    apply_url: str
    ats: str
    posted_at: Optional[datetime] = None

    @property
    def id(self) -> str:
        # Title is intentionally NOT part of the hash: companies rename postings
        # ("Senior" -> "Staff") without changing the apply_url, and we don't want
        # those to look like brand-new jobs.
        key = f"{self.company.lower()}::{self.apply_url}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
