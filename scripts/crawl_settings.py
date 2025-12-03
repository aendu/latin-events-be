import http.client
import logging
from pathlib import Path
from typing import Optional

TARGET_DAY_SPAN = 90

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
    "style",
    "labels",
]

DEFAULT_HEADERS = {
}

DATA_DIR = Path("data")
PUBLIC_DIR = Path("public")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) WebKit/537.36 (KHTML, like Gecko) Chrome/124.01",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6_8) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Fedora; Linux x86_64; rv:129.0) Firefox/129.0",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/127.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) WebKit/537.36 (KHTML, like Gecko) ",
    "Mozilla/5.0 (Android 14; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.02 Mobile Safari/537.36",
    "Mozilla/5.0 (Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/16.02.78 Mobile Safari/537.36",
    "Mozilla/5.0 (Android 13; OnePlus DN2103) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.78 Mobile Safari/537.36",
    "Mozilla/5.0 (Android 12; Pixel 6a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.98 Mobile Safari/537.36",
    "Mozilla/5.0 (Android 11; SM-A525F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.37 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) Mobile Safari/Version/15.7",
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Safari/89.1",
]


def build_headers(extra: Optional[dict] = None) -> dict:
    """
    Create a request header set with a realistic, randomly chosen User-Agent.
    Use per-request to vary the client fingerprint.
    """
    import random  # local to avoid polluting crawler modules

    headers = DEFAULT_HEADERS.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)
    if extra:
        headers.update(extra)
    return headers


def enable_http_logging() -> None:
    """
    Turn on verbose HTTP logging for requests/urllib3. Useful during debugging.
    """
    http.client.HTTPConnection.debuglevel = 0                ### 0, 1, 2 (highest level)
    logging.basicConfig(level=logging.WARN)
    logging.getLogger("urllib3").setLevel(logging.WARN)
    logging.getLogger("requests").setLevel(logging.WARN)
