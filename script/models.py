from pydantic import BaseModel, Field, field_validator, model_validator, HttpUrl, AliasPath
from typing import Optional
from datetime import date


class JobPosting(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
    job_type: str = ""
    experience_level: str = ""
    description: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    posted_date: Optional[date] = None
    apply_url: Optional[HttpUrl] = None
    source_url: Optional[HttpUrl] = None

    @field_validator("title", "company", "location", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("posted_date", mode="before")
    @classmethod
    def parse_date(cls, v) -> Optional[date]:
        if not v or isinstance(v, date):
            return v
        for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d/%m/%Y"):
            try:
                return date.fromisoformat(v) if fmt == "%Y-%m-%d" else date.strptime(v, fmt).date()
            except ValueError:
                continue
        return None

    @field_validator("job_type", mode="before")
    @classmethod
    def normalize_job_type(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v = v.lower().strip()
        aliases = {
            "full-time":  ["full-time", "full time", "permanent", "ft"],
            "part-time":  ["part-time", "part time", "pt"],
            "contract":   ["contract", "contractor", "freelance", "temp"],
            "internship": ["intern", "internship"],
            "remote":     ["remote", "work from home", "wfh"],
        }
        for normalized, variants in aliases.items():
            if v in variants:
                return normalized
        return v

    @field_validator("responsibilities", "requirements", "benefits", mode="before")
    @classmethod
    def drop_empty_strings(cls, v: list) -> list:
        return [item.strip() for item in v if item and item.strip()]

    @model_validator(mode="after")
    def infer_experience_level(self) -> "JobPosting":
        if self.experience_level:
            return self
        text = f"{self.title} {self.description}".lower()
        levels = {
            "senior":     ["senior", "sr.", "lead", "principal", "staff"],
            "mid":        ["mid-level", "mid level", "intermediate"],
            "junior":     ["junior", "jr.", "entry level", "entry-level", "graduate"],
            "internship": ["intern", "internship"],
        }
        for level, keywords in levels.items():
            if any(kw in text for kw in keywords):
                self.experience_level = level
                break
        return self


class JobPostingJsonLd(BaseModel):
    """Maps raw JSON-LD fields directly onto our schema via aliases."""
    title: str = Field("", alias="title")
    company: str = Field("", validation_alias=AliasPath("hiringOrganization", "name"))
    location: str = Field("", validation_alias=AliasPath("jobLocation", "address", "addressLocality"))
    salary: str = Field("", validation_alias=AliasPath("baseSalary", "value", "value"))
    job_type: str = Field("", alias="employmentType")
    description: str = Field("", alias="description")
    posted_date: Optional[date] = Field(None, alias="datePosted")
    apply_url: Optional[HttpUrl] = Field(None, alias="url")

    model_config = {"populate_by_name": True}

    def to_job_posting(self, source_url: Optional[str] = None) -> JobPosting:
        data = self.model_dump()
        if source_url:
            data["source_url"] = source_url
        # strip HTML from description (JSON-LD often includes it)
        if data.get("description"):
            from bs4 import BeautifulSoup
            data["description"] = BeautifulSoup(data["description"], "html.parser").get_text()
        return JobPosting(**data)