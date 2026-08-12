"""Shared helpers for the spreadsheet loaders."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterator

from ..config import LANGUAGES, ROOT, SOURCES

LANGUAGE_ALIASES: dict[str, str] = {
    "simplified chinese": "zh-cn",
    "chinese (simplified)": "zh-cn",
    "traditional chinese": "zh-tw",
    "chinese (traditional)": "zh-tw",
    "chinese": "zh-cn",
    "brazilian portuguese": "pt-br",
    "portuguese (brazil)": "pt-br",
    "japan": "ja",
    "korea": "ko",
    **{item["name_en"].lower(): item["code"] for item in LANGUAGES},
    **{item["code"]: item["code"] for item in LANGUAGES},
}


def find_source_file(filename: str) -> Path | None:
    """Locate an input spreadsheet in sources/ or at the repository root."""
    for candidate in (SOURCES / filename, ROOT / filename):
        if candidate.exists():
            return candidate
    return None


def language_from_text(text: str) -> str | None:
    """Infer a language code from a sheet name such as 'Japanese Sets'."""
    lowered = str(text).strip().lower()
    if lowered in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[lowered]
    # Longest alias first so 'simplified chinese' beats 'chinese'.
    for alias in sorted(LANGUAGE_ALIASES, key=len, reverse=True):
        if len(alias) > 2 and alias in lowered:
            return LANGUAGE_ALIASES[alias]
    return None


def match_columns(headers: list[str], synonyms: dict[str, tuple[str, ...]]) -> dict[str, str]:
    """Map canonical field name -> actual header, matching exactly then loosely."""
    lowered = {str(header).strip().lower(): header for header in headers}
    mapping: dict[str, str] = {}
    for field, options in synonyms.items():
        for option in options:
            if option in lowered:
                mapping[field] = lowered[option]
                break
        if field in mapping:
            continue
        for option in options:
            hit = next((original for low, original in lowered.items() if option in low), None)
            if hit is not None and hit not in mapping.values():
                mapping[field] = hit
                break
    return mapping


def cell(record: Any, mapping: dict[str, str], field: str) -> Any:
    header = mapping.get(field)
    if header is None:
        return None
    return record.get(header)


def is_latin(text: str | None) -> bool:
    """True when a name is written in the Latin alphabet (so it is a translation)."""
    if not text:
        return False
    letters = re.sub(r"[^^\w]", "", text, flags=re.UNICODE)
    if not letters:
        return False
    ascii_letters = sum(1 for char in letters if char.isascii())
    return ascii_letters / len(letters) > 0.7


def read_sheets(path: Path) -> Iterator[tuple[str, Any]]:
    import pandas as pd

    if path.suffix.lower() == ".csv":
        yield path.stem, pd.read_csv(path, dtype=str, keep_default_na=False)
        return
    for sheet_name, frame in pd.read_excel(path, sheet_name=None, dtype=object).items():
        yield sheet_name, frame
