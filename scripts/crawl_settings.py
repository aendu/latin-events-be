import http.client
import logging
import os
import random
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional

import requests

TARGET_DAY_SPAN = 90
REQUEST_DELAY_SECONDS = float(os.environ.get("CRAWLER_REQUEST_DELAY_SECONDS", "1.5"))
REQUEST_MAX_ATTEMPTS = int(os.environ.get("CRAWLER_REQUEST_MAX_ATTEMPTS", "4"))
REQUEST_BACKOFF_SECONDS = float(os.environ.get("CRAWLER_REQUEST_BACKOFF_SECONDS", "5"))
REQUEST_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

FIELDNAMES = [
    "date",
    "time",
    "name",
    "flyer",
    "url",
    "host",
    "city",
    "region",
    "source",
    "labels",
]

DEFAULT_HEADERS = {
}

DATA_DIR = Path("data")
PUBLIC_DIR = Path("public")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6_8) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Fedora; Linux x86_64; rv:129.0) Firefox/129.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Android 14; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Android 13; OnePlus DN2103) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Android 12; Pixel 6a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Android 11; SM-A525F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) Mobile Safari/Version/15.7",
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Safari/89.1",
]

RUN_USER_AGENT = random.choice(USER_AGENTS)
_last_request_at = 0.0


def build_headers(extra: Optional[dict] = None) -> dict:
    """
    Create a request header set with one realistic User-Agent per crawler run.
    """
    headers = DEFAULT_HEADERS.copy()
    headers["User-Agent"] = RUN_USER_AGENT
    if extra:
        headers.update(extra)
    return headers


def _wait_for_request_slot() -> None:
    global _last_request_at
    if REQUEST_DELAY_SECONDS <= 0:
        return
    elapsed = time.monotonic() - _last_request_at
    if elapsed < REQUEST_DELAY_SECONDS:
        time.sleep(REQUEST_DELAY_SECONDS - elapsed)


def _mark_request_finished() -> None:
    global _last_request_at
    _last_request_at = time.monotonic()


def _retry_after_seconds(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, retry_at.timestamp() - time.time())


def _backoff_delay(attempt: int, response: Optional[requests.Response] = None) -> float:
    retry_after = _retry_after_seconds(response.headers.get("Retry-After") if response else None)
    if retry_after is not None:
        return retry_after
    return REQUEST_BACKOFF_SECONDS * (2 ** (attempt - 1)) + random.uniform(0, 1)


def polite_get(
    session: requests.Session,
    url: str,
    *,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 30,
) -> requests.Response:
    """
    Perform a GET with shared throttling and bounded retries for temporary failures.
    """
    request_headers = build_headers(headers)
    last_error: Optional[requests.RequestException] = None
    for attempt in range(1, REQUEST_MAX_ATTEMPTS + 1):
        _wait_for_request_slot()
        try:
            response = session.get(
                url,
                params=params,
                headers=request_headers,
                timeout=timeout,
            )
            _mark_request_finished()
            if (
                response.status_code in REQUEST_RETRY_STATUS_CODES
                and attempt < REQUEST_MAX_ATTEMPTS
            ):
                logging.warning(
                    "GET %s returned %s; retrying attempt %s/%s",
                    response.url,
                    response.status_code,
                    attempt + 1,
                    REQUEST_MAX_ATTEMPTS,
                )
                time.sleep(_backoff_delay(attempt, response))
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            _mark_request_finished()
            last_error = exc
            if attempt >= REQUEST_MAX_ATTEMPTS:
                raise
            logging.warning(
                "GET %s failed with %s; retrying attempt %s/%s",
                url,
                exc,
                attempt + 1,
                REQUEST_MAX_ATTEMPTS,
            )
            time.sleep(_backoff_delay(attempt))
    if last_error:
        raise last_error
    raise RuntimeError(f"GET {url} failed without a response")


def enable_http_logging() -> None:
    """
    Turn on verbose HTTP logging for requests/urllib3. Useful during debugging.
    """
    http.client.HTTPConnection.debuglevel = 0                ### 0, 1, 2 (highest level)
    logging.basicConfig(level=logging.WARN)
    logging.getLogger("urllib3").setLevel(logging.WARN)
    logging.getLogger("requests").setLevel(logging.WARN)
