"""Load the curated sports spine: ``sports_database.xlsx`` + ``sports_cards.xlsx``.

Mirrors the Pokémon ``database.xlsx`` pattern: the sets workbook is the spine
for set identity (season, manufacturer, sport, set name); the cards workbook
fills checklist rows. When both are present this source wins within ``sports``
over seed JSON, combined checklists, TCDB and Beckett dumps.

Expected set columns: season / product_year, manufacturer, sport, set_name,
release_date, optional source_set_id / set_id, language.

Expected card columns: set_name or set_id, number, subject / subject_name,
parallel, variant_tags / notations, optional serial_number, serial_total /
print_run, display_name, language.
"""

from __future__ import annotations

from pathlib import Path

from ..normalize import clean_text, parse_date, slugify
from ..records import CardRecord, SetRecord, SourceData
from ._excel import cell, find_source_file, match_columns, read_sheets

SOURCE = "sports_database.xlsx"
SETS_FILE = "sports_database.xlsx"
CARDS_FILE = "sports_cards.xlsx"
GAME = "sports"

SET_SYNONYMS = {
    "product_year": ("product_year", "season", "year"),
    "manufacturer": ("manufacturer", "brand", "company"),
    "sport": ("sport", "league"),
    "set_name": ("set_name", "set", "set name", "product", "name"),
    "source_set_id": ("source_set_id", "set_id", "set id", "id"),
    "release_date": ("release_date", "release date", "released", "date"),
    "language": ("language", "lang"),
}

CARD_SYNONYMS = {
    "set_name": ("set_name", "set", "set name", "product"),
    "set_id": ("set_id", "set id", "source_set_id", "id"),
    "number": ("number", "card_number", "no.", "#"),
    "subject_name": ("subject_name", "subject", "player", "name"),
    "parallel": ("parallel", "variant", "finish"),
    "notations": ("notations", "variant_tags", "notes", "insert", "tags"),
    "serial_number": ("serial_number", "serial"),
    "print_run": ("print_run", "serial_total", "print run", "numbered"),
    "display_name": ("display_name", "label", "full name"),
    "language": ("language", "lang"),
}


def load() -> SourceData | None:
    sets_path = find_source_file(SETS_FILE)
    cards_path = find_source_file(CARDS_FILE)
    if sets_path is None and cards_path is None:
        return None

    data = SourceData(name=SOURCE)
    set_ids_by_name: dict[str, str] = {}

    if sets_path is not None:
        _load_sets(sets_path, data, set_ids_by_name)
    if cards_path is not None:
        _load_cards(cards_path, data, set_ids_by_name)

    return data if data.sets or data.cards else None


def _load_sets(path: Path, data: SourceData, set_ids_by_name: dict[str, str]) -> None:
    seen: set[str] = set()
    for _sheet_name, frame in read_sheets(path):
        if frame.empty:
            continue
        mapping = match_columns([str(column) for column in frame.columns], SET_SYNONYMS)
        if "set_name" not in mapping:
            continue
        for _, record in frame.iterrows():
            set_name = clean_text(cell(record, mapping, "set_name"))
            if not set_name:
                continue
            set_id = (
                clean_text(cell(record, mapping, "source_set_id"))
                or slugify(set_name)
            )
            if set_id in seen:
                continue
            seen.add(set_id)
            language = clean_text(cell(record, mapping, "language")) or "en"
            set_ids_by_name[set_name.casefold()] = set_id
            data.sets.append(
                SetRecord(
                    source=SOURCE,
                    game=GAME,
                    language=language,
                    source_set_id=set_id,
                    name=set_name,
                    name_en=set_name,
                    manufacturer=clean_text(cell(record, mapping, "manufacturer")),
                    sport=clean_text(cell(record, mapping, "sport")),
                    product_year=clean_text(cell(record, mapping, "product_year")),
                    release_date=parse_date(cell(record, mapping, "release_date")),
                )
            )


def _load_cards(path: Path, data: SourceData, set_ids_by_name: dict[str, str]) -> None:
    known_set_ids = {record.source_set_id for record in data.sets if record.source_set_id}

    for _sheet_name, frame in read_sheets(path):
        if frame.empty:
            continue
        mapping = match_columns([str(column) for column in frame.columns], CARD_SYNONYMS)
        if "number" not in mapping:
            continue
        for _, record in frame.iterrows():
            number = clean_text(cell(record, mapping, "number"))
            subject = clean_text(cell(record, mapping, "subject_name"))
            display = clean_text(cell(record, mapping, "display_name"))
            if not number or not (subject or display):
                continue

            set_name = clean_text(cell(record, mapping, "set_name"))
            set_id = clean_text(cell(record, mapping, "set_id"))
            if not set_id and set_name:
                set_id = set_ids_by_name.get(set_name.casefold()) or slugify(set_name)
            if not set_id:
                continue

            # Auto-seed a set row when cards reference a set not on the spine sheet.
            if set_id not in known_set_ids:
                known_set_ids.add(set_id)
                language = clean_text(cell(record, mapping, "language")) or "en"
                data.sets.append(
                    SetRecord(
                        source=SOURCE,
                        game=GAME,
                        language=language,
                        source_set_id=set_id,
                        name=set_name or set_id,
                        name_en=set_name or set_id,
                    )
                )
                if set_name:
                    set_ids_by_name[set_name.casefold()] = set_id

            language = clean_text(cell(record, mapping, "language")) or "en"
            parallel = clean_text(cell(record, mapping, "parallel"))
            notations = clean_text(cell(record, mapping, "notations"))
            serial = clean_text(cell(record, mapping, "serial_number"))
            print_run = _as_int(cell(record, mapping, "print_run"))
            label = display or _label(subject or "", notations, parallel, serial, print_run)

            data.cards.append(
                CardRecord(
                    source=SOURCE,
                    game=GAME,
                    language=language,
                    source_set_id=set_id,
                    number=number,
                    name=label,
                    name_en=label,
                    subject_name=subject,
                    parallel=parallel,
                    notations=notations,
                    serial_number=serial,
                    print_run=print_run,
                    display_name=label,
                )
            )


def _as_int(value) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _label(
    subject: str,
    notations: str | None,
    parallel: str | None,
    serial: str | None,
    print_run: int | None,
) -> str:
    parts = [subject] if subject else []
    if notations:
        parts.append(notations.replace(",", " - "))
    if parallel:
        parts.append(parallel)
    if serial and print_run:
        parts.append(f"{serial}/{print_run}")
    return " - ".join(parts) if parts else subject
