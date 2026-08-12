"""Load ``database.xlsx``: the hand-curated master set list.

One sheet per language ("English Sets", "Japanese Sets", ...) holding the
release order, set name, abbreviation, release date and series/era. It reaches
further back and wider than the API data, so it is used as the spine of the
set table. Sheets whose names are written in Latin script for a non-Latin
language (the Japanese and Chinese sheets use English translations) are stored
as ``name_en``.
"""

from __future__ import annotations

from ..normalize import clean_text, parse_date
from ..records import SetRecord, SourceData
from ._excel import cell, find_source_file, is_latin, language_from_text, match_columns, read_sheets

SOURCE = "database.xlsx"

SYNONYMS = {
    "sequence": ("#", "no.", "order", "index"),
    "name": ("set name", "name", "set"),
    "abbreviation": ("abbreviation", "abbr", "set code", "code"),
    "release_date": ("release date", "released", "date"),
    "series_name": ("series", "era", "block", "generation"),
}


def load() -> SourceData | None:
    path = find_source_file(SOURCE)
    if path is None:
        return None

    data = SourceData(name=SOURCE)

    for sheet_name, frame in read_sheets(path):
        language = language_from_text(sheet_name)
        if language is None or frame.empty:
            continue
        mapping = match_columns([str(column) for column in frame.columns], SYNONYMS)
        if "name" not in mapping:
            continue

        for _, record in frame.iterrows():
            name = clean_text(cell(record, mapping, "name"))
            if not name:
                continue
            abbreviation = clean_text(cell(record, mapping, "abbreviation"))
            sequence = clean_text(cell(record, mapping, "sequence"))
            translated = language != "en" and is_latin(name)
            data.sets.append(
                SetRecord(
                    source=SOURCE,
                    language=language,
                    source_set_id=abbreviation,
                    name=None if translated else name,
                    name_en=name if translated or language == "en" else None,
                    abbreviation=abbreviation,
                    release_date=parse_date(cell(record, mapping, "release_date")),
                    series_name=clean_text(cell(record, mapping, "series_name")),
                    sequence=int(float(sequence)) if sequence and _is_number(sequence) else None,
                )
            )

    return data if data.sets else None


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True
