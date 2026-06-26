import json
import re
from typing import Optional

from bs4 import BeautifulSoup

from models import JobPosting, JobPostingJsonLd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SALARY_RE = re.compile(
    r'[\$£€]\s?\d[\d,\.]*\s?(?:k|K)?(?:\s?[-–]\s?[\$£€]?\s?\d[\d,\.]*\s?(?:k|K)?)?'
    r'(?:\s?(?:per|\/)\s?\w+)?'
)

SECTION_KEYWORDS: dict[str, list[str]] = {
    "responsibilities": ["responsibilities", "what you'll do", "the role", "duties", "you will"],
    "requirements":     ["requirements", "qualifications", "what you'll need", "skills", "experience", "must have"],
    "benefits":         ["benefits", "perks", "what we offer", "compensation", "why join"],
}


# ---------------------------------------------------------------------------
# Structured data (JSON-LD) — always try this first
# ---------------------------------------------------------------------------

def extract_json_ld(soup: BeautifulSoup) -> dict:
    """Return the first JobPosting JSON-LD block found, or an empty dict."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            if isinstance(data, dict) and data.get("@type", "").lower() == "jobposting":
                return data
        except (json.JSONDecodeError, AttributeError):
            continue
    return {}


def parse_from_json_ld(data: dict, source_url: Optional[str] = None) -> Optional[JobPosting]:
    try:
        job = JobPostingJsonLd.model_validate(data).to_job_posting(source_url)
        assert isinstance(job, JobPosting)  # sanity check
        return job
    except Exception as e:
        logger.warning("JSON-LD parse failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# DOM helpers
# ---------------------------------------------------------------------------

def get_main_content(soup: BeautifulSoup) -> str:
    """Return the text of the most likely primary content block."""
    for selector in ["main", "article", "[role='main']", "#content", ".content"]:
        block = soup.select_one(selector)
        if block:
            return block.get_text(separator="\n", strip=True)
    return soup.body.get_text(separator="\n", strip=True) if soup.body else ""


def extract_salary(text: str) -> str:
    match = SALARY_RE.search(text)
    return match.group(0).strip() if match else ""


def extract_sections(soup: BeautifulSoup) -> dict[str, list[str]]:
    """
    Find headings whose text matches a known section keyword, then collect
    the <li> items from the next sibling <ul>/<ol>.
    """
    sections: dict[str, list[str]] = {k: [] for k in SECTION_KEYWORDS}

    for heading in soup.find_all(["h1", "h2", "h3", "h4", "strong"]):
        heading_text = heading.get_text(strip=True).lower()

        matched = next(
            (section for section, keywords in SECTION_KEYWORDS.items()
             if any(kw in heading_text for kw in keywords)),
            None,
        )
        if not matched:
            continue

        sibling = heading.find_next_sibling()
        while sibling and sibling.name not in ("ul", "ol", "h1", "h2", "h3"):
            sibling = sibling.find_next_sibling()

        if sibling and sibling.name in ("ul", "ol"):
            items = [li.get_text(strip=True) for li in sibling.find_all("li")]
            sections[matched].extend(items)

    return sections


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str:
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return el.get_text(strip=True)
    return ""


# ---------------------------------------------------------------------------
# DOM fallback parser — builds a JobPosting directly
# ---------------------------------------------------------------------------

def parse_from_dom(soup: BeautifulSoup, source_url: Optional[str] = None) -> JobPosting:
    full_text = soup.get_text(" ", strip=True)
    sections = extract_sections(soup)

    # model_validate on a dict returns a JobPosting instance
    return JobPosting.model_validate({
        "title": _first_text(soup, ["h1"]),
        "company": _first_text(soup, [
            "[class*='company']", "[class*='employer']", "[itemprop='name']",
        ]),
        "location": _first_text(soup, [
            "[class*='location']", "[class*='address']", "[itemprop='addressLocality']",
        ]),
        "salary": extract_salary(full_text),
        "job_type": _first_text(soup, ["[class*='job-type']", "[class*='employment']"]),
        "description": get_main_content(soup),
        "responsibilities": sections["responsibilities"],
        "requirements": sections["requirements"],
        "benefits": sections["benefits"],
        "apply_url": (
            soup.select_one("a[href*='apply']").get("href")
            if soup.select_one("a[href*='apply']") else None
        ),
        "source_url": source_url,
    })


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_job_posting(soup: BeautifulSoup, source_url: Optional[str] = None) -> JobPosting:
    """
    Parse a job posting page into a validated JobPosting model.

    Strategy:
      1. Look for JSON-LD structured data (reliable, fast).
      2. Fall back to DOM scraping if JSON-LD is absent or invalid.

    Args:
        soup:       Parsed BeautifulSoup object of the page.
        source_url: The URL the page was fetched from (stored on the model).

    Returns:
        A validated JobPosting instance.
    """
    json_ld = extract_json_ld(soup)
    if json_ld:
        job = parse_from_json_ld(json_ld, source_url)
        if job:
            return job

    return parse_from_dom(soup, source_url)