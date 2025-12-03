import re
from typing import Iterable, List, Optional, Sequence

VALID_STYLE_CODES = {"S", "B", "K", "Z", "O"}

# Individual style keywords are geared towards precision. Broad "latin" or "party"
# terms fall back to "O" (Other) to avoid false positives.
STYLE_KEYWORDS = {
    "S": [
        r"\bsalsa\b",
        r"\bcasino\b",
        r"\bson\b",
        r"\btimba\b",
        r"\bru(e|é)da\b",
        r"\bmambo\b",
        r"\bon\s*1\b",
        r"\bon\s*2\b",
        r"\bcubana\b",
        r"\bcuban\b",
    ],
    "B": [
        r"\bbachata\b",
        r"\bsensual\b",
        r"\bbachata\s*fusion\b",
        r"\bd(o|ó|minican)\s*bachata\b",
    ],
    "K": [
        r"\bkizomba\b",
        r"\burban\s*kiz+\b",
        r"\bkiz+\b",
        r"\bkizz\b",
        r"\bkiz\s*fusion\b",
    ],
    "Z": [
        r"\bzouk\b",
        r"\blambazouk\b",
        r"\bzouklove\b",
    ],
}

# Combined abbreviations that frequently appear in titles.
COMBINATION_PATTERNS = [
    (["S", "B", "K", "Z"], r"\bsbkz\b"),
    (["S", "B", "K"], r"\bsbk\b"),
    (["S", "B"], r"\bsb\b"),
    (["S", "Z"], r"\bsz\b"),
    (["B", "K"], r"\bbk\b"),
    (["B", "Z"], r"\bbz\b"),
]


def normalize_styles(styles: Iterable[str]) -> List[str]:
    unique = []
    for style in styles:
        code = style.strip().upper()
        if code in VALID_STYLE_CODES and code not in unique:
            unique.append(code)
    if not unique:
        unique.append("O")
    return sorted(unique)


def detect_styles(
    name: str,
    labels: Optional[Sequence[str]] = None,
    detail_text: Optional[str] = None,
    host: Optional[str] = None,
) -> List[str]:
    """
    Try to infer the dance styles an event covers from its name, labels and,
    when available, the detail page contents.
    """
    text_parts = [
        name or "",
        " ".join(labels or []),
        detail_text or "",
        host or "",
    ]
    haystack = " ".join(text_parts)
    folded = re.sub(r"\s+", " ", haystack).lower()

    styles: list[str] = []

    for combo_styles, pattern in COMBINATION_PATTERNS:
        if re.search(pattern, folded):
            styles.extend(combo_styles)

    for style_code, patterns in STYLE_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, folded):
                styles.append(style_code)
                break

    # Salsa/Bachata style abbreviations such as "SB party" may have been picked
    # up by the combination matcher already; leave the "Other" fallback only
    # when nothing was detected.
    if not styles:
        if "latin" in folded or "latino" in folded:
            styles.append("O")

    return normalize_styles(styles)


def styles_to_cell(styles: Iterable[str]) -> str:
    return "|".join(normalize_styles(styles))
