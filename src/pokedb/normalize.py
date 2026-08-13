"""Helpers for turning source rows into consistent database values."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

_NUMBER_RE = re.compile(r"^\s*(?P<prefix>[A-Za-z]*)[\s\-]*(?P<value>\d+)(?P<suffix>[A-Za-z]*)\s*$")

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d.%m.%Y",
    "%Y年%m月%d日",
    "%d %B %Y",
    "%B %d, %Y",
)


def split_number(number: str) -> tuple[str | None, int | None]:
    """Split a printed card number into its alpha prefix and numeric value.

    ``'001'`` -> ``(None, 1)``, ``'TG12'`` -> ``('TG', 12)``, ``'SWSH284'`` ->
    ``('SWSH', 284)``. Numbers that do not fit the pattern sort last.
    """
    match = _NUMBER_RE.match(str(number))
    if not match:
        return None, None
    prefix = match.group("prefix").upper() or None
    return prefix, int(match.group("value"))


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    # pandas represents blank spreadsheet cells as float NaN.
    if isinstance(value, float) and value != value:
        return None
    text = str(value).replace("\u00a0", " ").strip()
    if not text or text.lower() in {"nan", "nat", "none", "#n/a"}:
        return None
    return text


def parse_date(value: object) -> str | None:
    """Return an ISO-8601 date string, keeping partial (YYYY / YYYY-MM) dates."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    text = clean_text(value)
    if not text:
        return None
    if re.fullmatch(r"\d{4}", text):
        return text
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return text
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def release_year(release_date: str | None) -> int | None:
    if not release_date:
        return None
    head = release_date[:4]
    return int(head) if head.isdigit() else None


def normalize_code(value: object) -> str | None:
    """Fold a set code or identifier so the sources can be compared.

    Sources spell the same code differently (``CS1.5C`` / ``cs1.5c``,
    ``SV1S`` / ``sv1s``), so casing and punctuation are dropped.
    """
    text = clean_text(value)
    if not text:
        return None
    folded = re.sub(r"[^a-z0-9]+", "", text.lower())
    return folded or None


def normalize_name(value: object) -> str | None:
    """Fold a set name for comparison: Latin accents, case and punctuation removed.

    Accent folding is confined to Latin runs. Unicode also classes Japanese
    dakuten / handakuten and the long-vowel mark as diacritics; stripping them
    globally turns リザードン into リサトン and collapses different names.
    """
    text = clean_text(value)
    if not text:
        return None

    def _fold_latin_run(match: re.Match[str]) -> str:
        run = match.group(0)
        decomposed = unicodedata.normalize("NFKD", run)
        return "".join(char for char in decomposed if not unicodedata.combining(char))

    # Latin letters plus any combining marks attached to them.
    folded_latin = re.sub(r"[A-Za-z\u00C0-\u024F\u1E00-\u1EFF\u0300-\u036F]+", _fold_latin_run, text)
    folded = re.sub(r"[^0-9a-z\u3000-\u9fff\uac00-\ud7af]+", "", folded_latin.lower())
    return folded or None


def slugify(value: str, fallback: str = "set") -> str:
    text = normalize_code(value)
    if text:
        return text
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = re.sub(r"[^a-z0-9]+", "-", decomposed.lower()).strip("-")
    return ascii_only or fallback
