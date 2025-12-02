import csv
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin

from crawl_settings import (
    DATA_DIR,
    DEFAULT_HEADERS,
    build_headers,
    FIELDNAMES,
    enable_http_logging,
    TARGET_DAY_SPAN,
)
import requests
from bs4 import BeautifulSoup, Tag

LABEL_REPLACEMENTS = {
    "social dance": "party",
    "bachata party schweiz": "party",
}


def normalize_labels(raw_labels: Iterable[str]) -> List[str]:
    normalized = []
    for label in raw_labels:
        value = label.lower().strip()
        value = LABEL_REPLACEMENTS.get(value, value)
        if value and value not in normalized:
            normalized.append(value)
    return normalized

BASE_URL = "https://www.latino.ch"
LISTING_PATH = "/events"
OUTPUT_PATH = DATA_DIR / "events_latino_ch.csv"
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


def fetch_chunk(session: requests.Session, params: dict) -> str:
    headers = build_headers()
    if params.get("format") == "js":
        headers.update(
            {
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "text/javascript, text/html, application/xhtml+xml, */*",
            }
        )
    response = session.get(
        urljoin(BASE_URL, LISTING_PATH), params=params, headers=headers, timeout=30
    )
    response.raise_for_status()
    return response.text


def clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def extract_address(event_div: Tag) -> Tuple[str, str]:
    address = event_div.select_one(".address")
    if not address:
        return "", ""
    host = ""
    host_el = address.find("div", class_="line")
    if host_el:
        host = clean_text(host_el.get_text())
    city = ""
    city_el = address.find("b", class_="line")
    if city_el:
        city = clean_text(city_el.get_text())
    return host, city


def extract_url(event_div: Tag) -> str:
    parent_link = event_div.find_parent("a", href=True)
    if parent_link:
        return urljoin(BASE_URL, parent_link["href"])
    internal_link = event_div.find("a", href=True)
    if internal_link:
        return urljoin(BASE_URL, internal_link["href"])
    return ""


def extract_flyer(event_div: Tag) -> str:
    img_tag = event_div.find("img")
    if not img_tag or not img_tag.get("src"):
        return ""
    return urljoin(BASE_URL, img_tag["src"])


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
        if 7000 <= plz < 8000 or 8200 <= plz :
            return "Ost Schweiz"
    return "Region Zürich"


def build_events_from_cluster(event_div: Tag, event_date: str) -> Iterable[EventEntry]:
    host, city = extract_address(event_div)
    flyer = extract_flyer(event_div)
    url = extract_url(event_div)
    labels = normalize_labels(
        [
            clean_text(label.get_text())
            for label in event_div.select(".label")
            if clean_text(label.get_text())
        ]
    )
    region = determine_region(city)
    title_block = event_div.select_one(".title")
    if not title_block:
        return []
    entries: List[EventEntry] = []
    for item in title_block.select("li"):
        li_copy = BeautifulSoup(str(item), "html.parser")
        span = li_copy.find("span")
        time_text = ""
        if span:
            time_text = clean_text(span.get_text())
            span.extract()
        name_text = clean_text(li_copy.get_text())
        if not name_text:
            continue
        entries.append(
            EventEntry(
                date=event_date,
                time=time_text,
                name=name_text,
                flyer=flyer,
                url=url,
                host=host,
                city=city,
                region=region,
                source="latino.ch",
                labels=labels,
            )
        )
    return entries


def build_event_from_block(event_div: Tag, event_date: str) -> Iterable[EventEntry]:
    classes = event_div.get("class", [])
    if "cluster" in classes:
        return build_events_from_cluster(event_div, event_date)
    host, city = extract_address(event_div)
    time_el = event_div.select_one(".col-xs-5 span")
    title_el = event_div.select_one(".title")
    name = clean_text(title_el.get_text() if title_el else "")
    labels = normalize_labels(
        [
            clean_text(label.get_text())
            for label in event_div.select(".label")
            if clean_text(label.get_text())
        ]
    )
    region = determine_region(city)
    return [
        EventEntry(
            date=event_date,
            time=clean_text(time_el.get_text() if time_el else ""),
            name=name,
            flyer=extract_flyer(event_div),
            url=extract_url(event_div),
            host=host,
            city=city,
            region=region,
            source="latino.ch",
            labels=labels,
        )
    ]


def parse_events(html: str) -> Tuple[List[EventEntry], List[str]]:
    soup = BeautifulSoup(html, "html.parser")
    chunk_events: List[EventEntry] = []
    for event_div in soup.select("div.event"):
        header = event_div.find_previous("h3", attrs={"data-date": True})
        if not header:
            continue
        event_date = header.get("data-date")
        if not event_date:
            continue
        for entry in build_event_from_block(event_div, event_date.strip()):
            chunk_events.append(entry)
    date_markers = [
        clean_text(h.get("data-date")) for h in soup.select("h3[data-date]")
    ]
    date_markers = [d for d in date_markers if d]
    return chunk_events, date_markers


def write_csv(events: Sequence[EventEntry]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for event in events:
            writer.writerow(event.to_row())


def main() -> None:
    enable_http_logging()
    session = requests.Session()
    params = {"locale": "de"}
    html = fetch_chunk(session, params)
    seen_keys = set()
    collected: List[EventEntry] = []
    min_date: Optional[date] = None
    max_date: Optional[date] = None
    target_end_date = date.today() + timedelta(days=TARGET_DAY_SPAN)
    last_date_for_scroll: Optional[str] = None
    attempts_without_new = 0
    while True:
        chunk_events, chunk_dates = parse_events(html)
        added_this_round = 0
        for entry in chunk_events:
            key = (entry.date, entry.time, entry.name, entry.city)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            collected.append(entry)
            event_date = datetime.strptime(entry.date, "%Y-%m-%d").date()
            min_date = event_date if min_date is None else min(min_date, event_date)
            max_date = event_date if max_date is None else max(max_date, event_date)
            added_this_round += 1
        if chunk_dates:
            last_date_for_scroll = chunk_dates[-1]
        if max_date and max_date >= target_end_date:
            break
        if not chunk_dates or not last_date_for_scroll:
            break
        if added_this_round == 0:
            attempts_without_new += 1
            if attempts_without_new >= 2:
                break
        else:
            attempts_without_new = 0
        params = {"locale": "de", "format": "js", "filter[last_date]": last_date_for_scroll}
        html = fetch_chunk(session, params)
        if not html.strip():
            break
    if not collected:
        raise SystemExit("No events collected from latino.ch")
    collected.sort(
        key=lambda item: (
            item.date,
            clean_text(item.time),
            item.name.lower(),
        )
    )
    write_csv(collected)
    span_desc = (
        f"{min_date.isoformat()} – {max_date.isoformat()}"
        if min_date and max_date
        else "unknown range"
    )
    print(f"Wrote {len(collected)} events covering {span_desc} to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
