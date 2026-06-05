import csv
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Sequence
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from crawl_settings import (
    DATA_DIR,
    FIELDNAMES,
    TARGET_DAY_SPAN,
    enable_http_logging,
    polite_get,
)
from style_detection import detect_styles

BASE_URL = "https://dimelocantando.ch"
HOME_PATH = "/de-CH/home"
OUTPUT_PATH = DATA_DIR / "events-dimelocantando.csv"
VENUE = "DimeloCantando"
CITY = "3008 Bern"
REGION = "Region Bern"

MONTHS = {
    "januar": 1,
    "jan": 1,
    "februar": 2,
    "feb": 2,
    "märz": 3,
    "maerz": 3,
    "mrz": 3,
    "april": 4,
    "apr": 4,
    "mai": 5,
    "juni": 6,
    "jun": 6,
    "juli": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "oktober": 10,
    "okt": 10,
    "november": 11,
    "nov": 11,
    "dezember": 12,
    "dez": 12,
}

WEEKDAYS = {
    "montag": 0,
    "dienstag": 1,
    "mittwoch": 2,
    "donnerstag": 3,
    "freitag": 4,
    "samstag": 5,
    "sonntag": 6,
}

LATIN_KEYWORD_PATTERNS = [
    r"\blatin\b",
    r"\blatino\b",
    r"\blatina\b",
    r"\bsalsa\b",
    r"\bbachata\b",
    r"\bkizomba\b",
    r"\bzouk\b",
    r"\bmerengue\b",
    r"\breggaeton\b",
    r"\bcumbia\b",
    r"\bbossa\b",
    r"\bsamba\b",
    r"\btimba\b",
    r"\brumba\b",
    r"\bmambo\b",
    r"\bcha\s*cha\b",
    r"\bson\s+cubano\b",
    r"\bbolero(s)?\b",
    r"\bafro[-\s]?(cubano|cuban|venezolano|venezuelan|venezolanisch)\b",
    r"\bcuban(a|o)?\b",
    r"\bkubanisch(e|er|es|en)?\b",
]

DATE_RE = re.compile(
    r"\b(?P<day>\d{1,2})\.?\s+"
    r"(?P<month>januar|jan|februar|feb|märz|maerz|mrz|april|apr|mai|"
    r"juni|jun|juli|jul|august|aug|september|sep|oktober|okt|"
    r"november|nov|dezember|dez)"
    r"(?:\s+(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)


@dataclass
class EventEntry:
    date: str
    time: str
    name: str
    flyer: str
    url: str
    host: str
    city: str
    region: str
    source: str
    labels: Sequence[str]

    def to_row(self) -> dict:
        return {
            "date": self.date,
            "time": self.time,
            "name": self.name,
            "flyer": self.flyer,
            "url": self.url,
            "host": self.host,
            "city": self.city,
            "region": self.region,
            "source": self.source,
            "labels": "|".join(sorted(set(self.labels))),
        }


def clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.replace("\ufeff", " ")).strip()


def fetch_page(session: requests.Session, url: str) -> str:
    response = polite_get(session, url, timeout=30)
    return response.text


def normalize_month(value: str) -> Optional[int]:
    return MONTHS.get(value.lower().replace("ä", "ae"))


def collect_text_after_heading(heading: Tag, title: str) -> str:
    parts: List[str] = []
    for node in heading.next_elements:
        if (
            isinstance(node, Tag)
            and node is not heading
            and node.name in {"h1", "h2", "h3", "h4", "h5", "h6"}
        ):
            break
        if not isinstance(node, NavigableString):
            continue
        text = clean_text(str(node))
        if not text or text.lower() in {title.lower(), "flyer"}:
            continue
        parts.append(text)
    return clean_text(" ".join(parts))


def extract_event_links(home_html: str) -> List[tuple[str, str, str]]:
    soup = BeautifulSoup(home_html, "html.parser")
    events_heading = soup.find(
        lambda tag: isinstance(tag, Tag)
        and tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}
        and "unsere veranstaltungen" in clean_text(tag.get_text()).lower()
    )
    if not events_heading:
        return []

    links: List[tuple[str, str, str]] = []
    seen_urls = set()
    for node in events_heading.find_all_next(
        ["h1", "h2", "h3", "h4", "h5", "h6", "a"]
    ):
        text = clean_text(node.get_text(" "))
        if node.name in {"h1", "h2", "h3", "h4", "h5", "h6"} and text.lower() in {
            "kontakt",
            "hinweis:",
        }:
            break
        if node.name != "a":
            continue
        href = node.get("href")
        if not href or not re.search(r"home!\d+", href):
            continue
        if text.lower() == "flyer":
            continue
        url = urljoin(BASE_URL, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        heading = node.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"])
        home_text = collect_text_after_heading(heading, text) if heading else ""
        links.append((text, url, home_text))
    return links


def page_lines(soup: BeautifulSoup) -> List[str]:
    return [line for line in (clean_text(value) for value in soup.stripped_strings) if line]


def extract_detail_lines(soup: BeautifulSoup, title: str) -> List[str]:
    lines = page_lines(soup)
    start = 0
    for index, line in enumerate(lines):
        if line.lower() == title.lower():
            start = index + 1
            break

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].lower() in {"kontakt", "hinweis:"}:
            end = index
            break
    return lines[start:end]


def extract_flyer(soup: BeautifulSoup) -> str:
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        descriptor = clean_text(
            " ".join([src, img.get("alt", ""), img.get("title", "")])
        ).lower()
        if (
            "logo" in descriptor
            or "language" in descriptor
            or "flagcdn.com" in descriptor
        ):
            continue
        return urljoin(BASE_URL, src)
    return ""


def extract_time(text: str) -> str:
    match = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", text)
    if not match:
        return ""
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def parse_single_dates(text: str) -> List[date]:
    today = date.today()
    target_end_date = today + timedelta(days=TARGET_DAY_SPAN)
    parsed_dates: List[date] = []
    for match in DATE_RE.finditer(text):
        month = normalize_month(match.group("month"))
        if not month:
            continue
        year = int(match.group("year") or today.year)
        candidate = date(year, month, int(match.group("day")))
        if not match.group("year") and candidate < today:
            candidate = date(year + 1, month, int(match.group("day")))
        if today <= candidate <= target_end_date and candidate not in parsed_dates:
            parsed_dates.append(candidate)
    return parsed_dates


def expand_recurring_dates(text: str) -> List[date]:
    match = re.search(
        r"\bjeden\s+(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return []
    target_weekday = WEEKDAYS[match.group(1).lower()]
    today = date.today()
    target_end_date = today + timedelta(days=TARGET_DAY_SPAN)
    current = today + timedelta(days=(target_weekday - today.weekday()) % 7)
    dates: List[date] = []
    while current <= target_end_date:
        dates.append(current)
        current += timedelta(days=7)
    return dates


def extract_event_dates(text: str) -> List[date]:
    return expand_recurring_dates(text) or parse_single_dates(text)


def build_labels(text: str) -> List[str]:
    labels: List[str] = []
    if re.search(r"\b(party|noche|jam|karaoke)\b", text, re.IGNORECASE):
        labels.append("party")
    return labels


def is_latin_event(
    name: str, labels: Sequence[str], detail_text: str, styles: Sequence[str]
) -> bool:
    if styles:
        return True
    haystack = clean_text(f"{name} {' '.join(labels)} {detail_text}").lower()
    return any(
        re.search(pattern, haystack, re.IGNORECASE)
        for pattern in LATIN_KEYWORD_PATTERNS
    )


def build_entries_from_detail(
    session: requests.Session, fallback_title: str, url: str, home_text: str
) -> List[EventEntry]:
    detail_html = fetch_page(session, url)
    soup = BeautifulSoup(detail_html, "html.parser")
    title = fallback_title
    detail_lines = extract_detail_lines(soup, title)
    detail_text = clean_text(f"{home_text} {' '.join(detail_lines)}")
    event_dates = extract_event_dates(detail_text)
    if not event_dates:
        return []

    labels = build_labels(f"{title} {detail_text}")
    styles = detect_styles(title, labels, detail_text, VENUE)
    if not is_latin_event(title, labels, detail_text, styles):
        return []

    flyer = extract_flyer(soup)
    time_value = extract_time(detail_text)
    return [
        EventEntry(
            date=event_date.isoformat(),
            time=time_value,
            name=title,
            flyer=flyer,
            url=url,
            host=VENUE,
            city=CITY,
            region=REGION,
            source="dimelocantando.ch",
            labels=labels,
        )
        for event_date in event_dates
    ]


def write_csv(events: Sequence[EventEntry]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        for event in events:
            writer.writerow(event.to_row())


def main() -> None:
    enable_http_logging()
    session = requests.Session()
    home_html = fetch_page(session, urljoin(BASE_URL, HOME_PATH))
    event_links = extract_event_links(home_html)
    if not event_links:
        raise SystemExit("No event links found on dimelocantando.ch")

    seen_keys = set()
    collected: List[EventEntry] = []
    for title, url, home_text in event_links:
        for entry in build_entries_from_detail(session, title, url, home_text):
            key = (entry.date, entry.time, entry.name, entry.city)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            collected.append(entry)

    if not collected:
        raise SystemExit("No Latin events collected from dimelocantando.ch")
    collected.sort(
        key=lambda item: (
            item.date,
            clean_text(item.time),
            item.name.lower(),
        )
    )
    write_csv(collected)
    print(f"Wrote {len(collected)} events to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
