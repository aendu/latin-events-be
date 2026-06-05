import csv
import logging
import re
import shutil
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable

from crawl_events_bachata_bern_ch import main as crawl_bachata
from crawl_events_dimelocantando_ch import main as crawl_dimelocantando
from crawl_events_latino_ch import main as crawl_latino
from crawl_settings import (
    DATA_DIR,
    FIELDNAMES,
    PUBLIC_DIR,
    enable_http_logging,
)

ALL_EVENTS_PATH = DATA_DIR / "events.csv"
PUBLIC_ALL_EVENTS_PATH = PUBLIC_DIR / "events.csv"


def read_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            row = {field: row.get(field, "") for field in FIELDNAMES}
            row.setdefault("source", "")
            rows.append(row)
        return rows


def normalize_name(name: str) -> str:
    # Lowercase and strip punctuation/extra whitespace for fuzzy comparison.
    cleaned = re.sub(r"[^a-z0-9]+", " ", name.lower())
    return cleaned.strip()


def names_similar(a: str, b: str, threshold: float = 1) -> bool:
    if not a or not b:
        return False
    if normalize_name(a) == normalize_name(b):
        return True
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio() >= threshold


def dedupe_and_sort(rows: list[dict]) -> list[dict]:
    unique: list[dict] = []
    for row in rows:
        date = row.get("date", "")
        name = row.get("name", "")
        if not date or not name:
            continue
        is_duplicate = False
        for existing in unique:
            if existing.get("date", "") != date:
                continue
            if names_similar(existing.get("name", ""), name):
                is_duplicate = True
                break
        if not is_duplicate:
            unique.append(row)
    unique.sort(
        key=lambda item: (
            item.get("date", ""),
            item.get("time", ""),
            (item.get("name") or "").lower(),
        )
    )
    return unique


def write_all_events(rows: list[dict]) -> None:
    ALL_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ALL_EVENTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    PUBLIC_ALL_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ALL_EVENTS_PATH, PUBLIC_ALL_EVENTS_PATH)


def run_source_crawler(name: str, crawler: Callable[[], None], output_path: Path) -> bool:
    try:
        crawler()
        return True
    except SystemExit as exc:
        error = exc
    except Exception as exc:
        error = exc
    if output_path.exists():
        logging.warning(
            "%s crawler failed with %s; reusing existing %s",
            name,
            error,
            output_path,
        )
        return False
    logging.warning(
        "%s crawler failed with %s and no fallback CSV exists at %s; skipping source",
        name,
        error,
        output_path,
    )
    return False


def main() -> None:
    enable_http_logging()
    source_status = {
        "latino.ch": run_source_crawler(
            "latino.ch", crawl_latino, DATA_DIR / "events_latino_ch.csv"
        ),
        "bachata-bern.ch": run_source_crawler(
            "bachata-bern.ch", crawl_bachata, DATA_DIR / "events-bachata-bern.csv"
        ),
        "dimelocantando.ch": run_source_crawler(
            "dimelocantando.ch",
            crawl_dimelocantando,
            DATA_DIR / "events-dimelocantando.csv",
        ),
    }
    latino_rows = read_events(DATA_DIR / "events_latino_ch.csv")
    bachata_rows = read_events(DATA_DIR / "events-bachata-bern.csv")
    dimelocantando_rows = read_events(DATA_DIR / "events-dimelocantando.csv")
    combined = dedupe_and_sort(latino_rows + bachata_rows + dimelocantando_rows)
    if not combined:
        raise SystemExit("No events found to combine")
    write_all_events(combined)
    failed_sources = [name for name, succeeded in source_status.items() if not succeeded]
    if failed_sources:
        print(f"Reused fallback data for: {', '.join(failed_sources)}")
    print(
        f"Wrote {len(combined)} combined events to {ALL_EVENTS_PATH} and {PUBLIC_ALL_EVENTS_PATH}"
    )


if __name__ == "__main__":
    main()
