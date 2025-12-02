import csv
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin

import requests

from crawl_settings import (
    DATA_DIR,
    DEFAULT_HEADERS,
    FIELDNAMES,
    TARGET_DAY_SPAN,
)

LABEL_REPLACEMENTS = {
    "social dance": "party",
    "bachata party schweiz": "party",
}


def normalize_labels(raw_labels: Iterable[str]) -> List[str]:
    normalized: List[str] = []
    for label in raw_labels:
        value = label.lower().strip()
        value = LABEL_REPLACEMENTS.get(value, value)
        if value and value not in normalized:
            normalized.append(value)
    return normalized

BASE_URL = "https://bachata-bern.ch"
API_PATH = "/wp-json/tribe/events/v1/events/"
OUTPUT_PATH = DATA_DIR / "events-bachata-bern.csv"
HEADERS = DEFAULT_HEADERS


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
            "labels": "|".join(sorted(set(self.labels))),
        }


def clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def determine_region(city_text: str) -> str:
    if not city_text:
        return "Region Zürich"
    lc = city_text.lower()
    city_based = {
        "bern": "Region Bern",
        "thun": "Region Bern",
        "biel": "Region Bern",
        "fribourg": "Region Bern",
        "fribourg/fribourg": "Region Bern",
        "fribourg/friburg": "Region Bern",
        "friburg": "Region Bern",
        "düdingen": "Region Bern",
        "zürich": "Region Zürich",
        "zuerich": "Region Zürich",
        "zurich": "Region Zürich",
        "winterthur": "Region Zürich",
        "schaffhausen": "Ost Schweiz",
        "luzern": "Zentral Schweiz",
        "kriens": "Zentral Schweiz",
        "rotkreuz": "Zentral Schweiz",
        "zug": "Zentral Schweiz",
        "solothurn": "Region Solothurn & Aarau",
        "aarau": "Region Solothurn & Aarau",
        "wohlen": "Region Solothurn & Aarau",
        "olten": "Region Solothurn & Aarau",
        "st. gallen": "Ost Schweiz",
        "st gallen": "Ost Schweiz",
        "st.gallen": "Ost Schweiz",
        "chur": "Ost Schweiz",
        "konstanz": "Ost Schweiz",
        "rapperswil-jona": "Ost Schweiz",
        "lausanne": "West Schweiz",
        "geneva": "West Schweiz",
        "genève": "West Schweiz",
        "neuchâtel": "West Schweiz",
        "neuchatel": "West Schweiz",
        "sion": "Wallis",
        "martigny": "Wallis",
        "brig": "Wallis",
        "lugano": "Tessin",
        "locarno": "Tessin",
        "basel": "Region Basel",
    }
    for needle, region in city_based.items():
        if needle in lc:
            return region
    match = re.search(r"(\d{4})", city_text)
    if match:
        plz = int(match.group(1))
        if 1000 <= plz < 1700 or 2000 <= plz < 3000:
            return "West Schweiz"
        if 1700 <= plz < 1800 or 3000 <= plz < 3900:
            return "Region Bern"
        if 1800 <= plz < 2000 or 3900 <= plz < 4000:
            return "Wallis"
        if 4000 <= plz < 4500:
            return "Region Basel"
        if 4500 <= plz < 6000:
            return "Region Solothurn & Aarau"
        if 6000 <= plz < 6500:
            return "Zentral Schweiz"
        if 6500 <= plz < 7000:
            return "Tessin"
        if 7000 <= plz < 8000 or 8200 <= plz:
            return "Ost Schweiz"
    return "Region Zürich"


def fetch_events(session: requests.Session) -> List[dict]:
    today = date.today()
    end_date = today + timedelta(days=TARGET_DAY_SPAN)
    params = {
        "page": 1,
        "per_page": 100,
        "start_date": f"{today.isoformat()} 00:00:00",
        "end_date": f"{end_date.isoformat()} 23:59:59",
        "status": "publish",
    }
    events: List[dict] = []
    while True:
        response = session.get(
            urljoin(BASE_URL, API_PATH), params=params, headers=HEADERS, timeout=30
        )
        response.raise_for_status()
        data = response.json()
        events.extend(data.get("events", []))
        total_pages = data.get("total_pages") or 1
        if params["page"] >= total_pages:
            break
        params["page"] += 1
    return events


def build_city(venue: dict) -> str:
    parts = []
    if venue.get("zip"):
        parts.append(str(venue["zip"]))
    if venue.get("city"):
        parts.append(venue["city"])
    if not parts and venue.get("address"):
        parts.append(venue["address"])
    return clean_text(" ".join(parts))


def build_host(organizers: Iterable[dict]) -> str:
    for org in organizers or []:
        name = clean_text(org.get("organizer"))
        if name:
            return name
    return ""


def build_labels(item: dict) -> List[str]:
    labels: List[str] = []
    for cat in item.get("categories") or []:
        label = clean_text(cat.get("name"))
        if label:
            labels.append(label)
    for tag in item.get("tags") or []:
        label = clean_text(tag.get("name"))
        if label:
            labels.append(label)
    return normalize_labels(labels)


def build_event_entry(item: dict) -> EventEntry:
    start_text = item.get("start_date")
    start_dt = datetime.fromisoformat(start_text) if start_text else None
    date_value = start_dt.date().isoformat() if start_dt else ""
    time_value = start_dt.strftime("%H:%M") if start_dt else ""
    venue = item.get("venue") or {}
    city = build_city(venue)
    image = item.get("image") or {}
    flyer = image.get("url") or ""
    return EventEntry(
        date=date_value,
        time=time_value,
        name=clean_text(item.get("title")),
        flyer=flyer,
        url=item.get("url") or "",
        host=build_host(item.get("organizer")),
        city=city,
        region=determine_region(city),
        labels=build_labels(item),
    )


def write_csv(events: Sequence[EventEntry]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for event in events:
            writer.writerow(event.to_row())


def main() -> None:
    session = requests.Session()
    raw_events = fetch_events(session)
    if not raw_events:
        raise SystemExit("No events retrieved from bachata-bern.ch")
    target_end_date = date.today() + timedelta(days=TARGET_DAY_SPAN)
    seen_keys = set()
    collected: List[EventEntry] = []
    for item in raw_events:
        entry = build_event_entry(item)
        if not entry.date:
            continue
        event_date = datetime.strptime(entry.date, "%Y-%m-%d").date()
        if event_date > target_end_date:
            continue
        if event_date < date.today():
            continue
        key = (entry.date, entry.time, entry.name, entry.city)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        collected.append(entry)
    if not collected:
        raise SystemExit("No events collected from bachata-bern.ch")
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
