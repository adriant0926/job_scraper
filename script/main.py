import json
import logging
from typing import Optional

from fetcher import fetch
from parser import parse_job_posting
from models import JobPosting
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def save_jobs(jobs: list[JobPosting], path: str = "jobs.json") -> None:
    output = [job for job in jobs]
    Path(path).write_text(json.dumps(output, indent=2, default=str))
    print(f"Saved {len(jobs)} jobs to {path}")

def scrape_job(url: str) -> Optional[JobPosting]:
    """
    Fetch and parse a single job posting URL into a validated JobPosting.

    Returns None if fetching or parsing fails, so batch runs don't abort.
    """
    try:
        soup = fetch(url)
        job = parse_job_posting(soup, source_url=url)
        logger.info("Scraped: %s @ %s", job.title or "(no title)", job.company or "(no company)")
        return job
    except Exception as e:
        logger.error("Failed to scrape %s: %s", url, e)
        return None


def scrape_jobs(urls: list[str]) -> list[JobPosting]:
    results = []
    for url in urls:
        job = scrape_job(url)
        if job and isinstance(job, JobPosting):  # guard against dicts slipping through
            results.append(job)
    return results


if __name__ == "__main__":
    urls = [
        "https://iworkfor.nsw.gov.au/jobs/all-keywords/all-agencies/all-organisations-entities/information-and-communications-technology-jobs/all-locations/full-time-jobs?jobcategoryid=10352&worktypeid=10826&salarymin=105000",
        "https://careers.nab.com.au/jobs/search?page=1&cities%5B%5D=Australia-wide&query=",
        "https://cba.wd3.myworkdayjobs.com/CommBank_Careers?locationRegionStateProvince=c7cff0e46d864ae49ef40b4ba71e7e5c&jobFamilyGroup=089636baad99015305bcc5419301256c&jobFamily=31796cc3cc87016f37f1e7a4fd42815f",
        "https://recruitment.macquarie.com/en_US/careers/SearchJobs/?10671=%5B871429%5D&10671_format=21337&10672=%5B887281%5D&10672_format=21338&1270=%5B347511%5D&1270_format=3248&listFilterMode=1&jobRecordsPerPage=9&",


    ]

    jobs = scrape_jobs(urls)

    # pretty-print as JSON
    output = [job.model_dump(exclude_none=True) for job in jobs]
    print(json.dumps(output, indent=2, default=str))

    save_jobs(output, "jobs.json")