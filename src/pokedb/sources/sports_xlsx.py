"""Load curated sports checklists from ``sports_checklists.xlsx``.

Expected columns (headers are matched fuzzily):

    manufacturer, sport, product_year / season, set_name, set_id,
    subject_name, parallel, notations, number, serial_number, print_run,
    display_name, language, release_date
"""

from __future__ import annotations

from ..normalize import clean_text, parse_date
from ..records import CardRecord, SetRecord, SourceData
from ._excel import cell, find_source_file, match_columns, read_sheets

SOURCE = "sports_checklists.xlsx"
GAME = "sports"

SYNONYMS = {
    "manufacturer": ("manufacturer", "brand", "company"),
    "sport": ("sport", "league"),
    "product_year": ("product_year", "season", "year"),
    "set_name": ("set_name", "set", "set name", "product"),
    "set_id": ("set_id", "set id", "id"),
    "subject_name": ("subject_name", "player", "subject", "name"),
    "parallel": ("parallel", "variant", "finish"),
    "notations": ("notations", "notes", "insert"),
    "number": ("number", "card_number", "no.", "#"),
    "serial_number": ("serial_number", "serial"),
    "print_run": ("print_run", "print run", "numbered"),
    "display_name": ("display_name", "label", "full name"),
    "language": ("language", "lang"),
    "release_date": ("release_date", "release date", "released"),
}


def load() -> SourceData | None:
    path = find_source_file(SOURCE)
    if path is None:
        return None

    data = SourceData(name=SOURCE)
    seen_sets: set[str] = set()

    for _sheet_name, frame in read_sheets(path):
        if frame.empty:
            continue
        mapping = match_columns([str(column) for column in frame.columns], SYNONYMS)
        if "set_name" not in mapping or "number" not in mapping:
            continue

        for _, record in frame.iterrows():
            set_name = clean_text(cell(record, mapping, "set_name"))
            number = clean_text(cell(record, mapping, "number"))
            subject = clean_text(cell(record, mapping, "subject_name"))
            display = clean_text(cell(record, mapping, "display_name"))
            if not set_name or not number or not (subject or display):
                continue

            set_id = clean_text(cell(record, mapping, "set_id")) or set_name
            language = clean_text(cell(record, mapping, "language")) or "en"
            if set_id not in seen_sets:
                seen_sets.add(set_id)
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

            parallel = clean_text(cell(record, mapping, "parallel"))
            notations = clean_text(cell(record, mapping, "notations"))
            serial = clean_text(cell(record, mapping, "serial_number"))
            print_run_raw = clean_text(cell(record, mapping, "print_run"))
            print_run = int(float(print_run_raw)) if print_run_raw and print_run_raw.replace(".", "", 1).isdigit() else None
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

    return data if data.sets else None


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
