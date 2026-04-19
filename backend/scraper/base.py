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
        key = f"{self.company.lower()}::{self.title.lower()}::{self.apply_url}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
