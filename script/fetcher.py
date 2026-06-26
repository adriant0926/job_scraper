import time
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def fetch(
    url: str,
    headers: Optional[dict] = None,
    retries: int = 3,
    backoff: float = 2.0,
    timeout: int = 10,
) -> BeautifulSoup:
    """
    Fetch a URL and return a parsed BeautifulSoup object.

    Retries on transient failures (5xx, connection errors) with
    exponential backoff. Raises on 4xx or after all retries are exhausted.

    Args:
        url:     Page to fetch.
        headers: Optional header overrides (merged with defaults).
        retries: Max number of attempts.
        backoff: Base seconds to wait between retries (doubles each attempt).
        timeout: Request timeout in seconds.
    """
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=merged_headers, timeout=timeout)

            if response.status_code == 429:
                wait = backoff * (2 ** attempt)
                logger.warning("Rate limited on %s — waiting %.1fs", url, wait)
                time.sleep(wait)
                continue

            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")

        except requests.exceptions.HTTPError as e:
            if response.status_code < 500:
                raise  # 4xx errors won't recover with a retry
            logger.warning("HTTP %s on attempt %d/%d for %s", e, attempt, retries, url)

        except requests.exceptions.ConnectionError:
            logger.warning("Connection error on attempt %d/%d for %s", attempt, retries, url)

        if attempt < retries:
            time.sleep(backoff * attempt)

    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")