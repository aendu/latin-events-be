from pathlib import Path

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
    "labels",
]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Android 14; Pixel 8)"
    )
}

DATA_DIR = Path("data")
PUBLIC_DIR = Path("public")
