"""Write the Excel workbook (and optional CSVs) from the built database.

The workbook is the deliverable: one file holding every set and card in every
language, with an autofilter on each sheet so a card can be found by set name,
number or card name. It is regenerated from scratch on every update, so edits
belong in the source spreadsheets rather than in the output file.
"""

from __future__ import annotations

import csv
import gzip
import sqlite3
from pathlib import Path

from .config import DB_PATH, EXPORTS

WORKBOOK_NAME = "Pokemon_TCG_Card_Database.xlsx"

# The four fields the workbook is built around - set name, card number, card
# name and release year - come first; the rest is context for non-Latin sets.
CARD_QUERY = """
SELECT
    language_name        AS "Language",
    set_name             AS "Set Name",
    card_number          AS "Card Number",
    card_name            AS "Card Name",
    release_year         AS "Year",
    set_name_en          AS "Set Name (EN)",
    card_name_en         AS "Card Name (EN)",
    set_abbreviation     AS "Set Code",
    release_date         AS "Release Date",
    card_count           AS "Cards In Set"
FROM (
    SELECT c.language, l.name_en AS language_name, s.name AS set_name,
           s.name_en AS set_name_en, s.abbreviation AS set_abbreviation,
           s.release_date, s.release_year, c.number AS card_number,
           c.number_prefix, c.number_value, c.name AS card_name,
           c.name_en AS card_name_en,
           COALESCE(s.card_count_official, s.card_count_loaded) AS card_count
    FROM cards c
    JOIN sets s      ON s.set_uid = c.set_uid
    JOIN languages l ON l.code = c.language
)
ORDER BY language, COALESCE(release_date, '9999'), set_name,
         COALESCE(number_prefix, ''), COALESCE(number_value, 999999), card_number
"""

SET_QUERY = """
SELECT
    l.name_en                    AS "Language",
    s.name                       AS "Set Name",
    s.name_en                    AS "Set Name (EN)",
    s.abbreviation               AS "Set Code",
    s.release_year               AS "Year",
    s.release_date               AS "Release Date",
    s.series_name                AS "Series",
    s.card_count_official        AS "Cards In Set",
    s.card_count_loaded          AS "Cards Listed",
    s.sources                    AS "Sources"
FROM sets s
JOIN languages l ON l.code = s.language
ORDER BY s.language, COALESCE(s.release_date, '9999'), s.name
"""

COVERAGE_QUERY = """
SELECT language_name AS "Language", language AS "Code", sets AS "Sets",
       sets_with_cards AS "Sets With Cards", cards AS "Cards",
       first_release AS "First Release", latest_release AS "Latest Release"
FROM coverage_by_language
ORDER BY cards DESC, sets DESC
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(f"{db_path} not found - run `python -m pokedb build` first")
    return sqlite3.connect(db_path)


def _fetch(connection: sqlite3.Connection, query: str) -> tuple[list[str], list[tuple]]:
    cursor = connection.execute(query)
    return [column[0] for column in cursor.description], cursor.fetchall()


def export_all(db_path: Path = DB_PATH, write_csv: bool = True) -> list[Path]:
    EXPORTS.mkdir(parents=True, exist_ok=True)
    connection = _connect(db_path)

    card_headers, card_rows = _fetch(connection, CARD_QUERY)
    set_headers, set_rows = _fetch(connection, SET_QUERY)
    coverage_headers, coverage_rows = _fetch(connection, COVERAGE_QUERY)
    built_at = connection.execute(
        "SELECT value FROM build_info WHERE key = 'built_at'"
    ).fetchone()
    sources = connection.execute(
        "SELECT value FROM build_info WHERE key = 'source_order'"
    ).fetchone()
    connection.close()

    written = [
        _write_workbook(
            card_headers,
            card_rows,
            set_headers,
            set_rows,
            coverage_headers,
            coverage_rows,
            built_at[0] if built_at else "",
            sources[0] if sources else "",
        )
    ]

    if write_csv:
        written.append(_write_csv(set_headers, set_rows, EXPORTS / "sets.csv"))
        written.append(
            _write_csv(card_headers, card_rows, EXPORTS / "cards.csv.gz", compress=True)
        )
    return written


def _write_csv(headers: list[str], rows, path: Path, compress: bool = False) -> Path:
    opener = (
        (lambda: gzip.open(path, "wt", newline="", encoding="utf-8"))
        if compress
        else (lambda: path.open("w", newline="", encoding="utf-8-sig"))
    )
    with opener() as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def _write_workbook(
    card_headers,
    card_rows,
    set_headers,
    set_rows,
    coverage_headers,
    coverage_rows,
    built_at: str,
    sources: str,
) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    path = EXPORTS / WORKBOOK_NAME
    workbook = Workbook()
    workbook.remove(workbook.active)

    widths = {
        "Language": 20, "Set Name": 38, "Set Name (EN)": 38, "Card Name": 30,
        "Card Name (EN)": 30, "Card Number": 14, "Year": 8, "Set Code": 12,
        "Release Date": 14, "Cards In Set": 13, "Cards Listed": 13, "Series": 26,
        "Sources": 30, "Code": 8, "Sets": 8, "Cards": 10, "Sets With Cards": 16,
        "First Release": 14, "Latest Release": 14,
    }

    def add_sheet(title: str, headers: list[str], rows) -> None:
        sheet = workbook.create_sheet(title)
        sheet.append(headers)
        for row in rows:
            sheet.append(list(row))
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(vertical="center")
        sheet.freeze_panes = "A2"
        if rows:
            sheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(rows) + 1}"
        for index, header in enumerate(headers, start=1):
            sheet.column_dimensions[get_column_letter(index)].width = widths.get(header, 16)

    add_sheet("Cards", card_headers, card_rows)
    add_sheet("Sets", set_headers, set_rows)
    add_sheet("Coverage", coverage_headers, coverage_rows)

    about = workbook.create_sheet("About")
    about.column_dimensions["A"].width = 26
    about.column_dimensions["B"].width = 96
    notes = [
        ("Pokemon TCG Card Database", ""),
        ("Generated", built_at),
        ("Sources", sources),
        ("Cards", f"{len(card_rows):,} rows"),
        ("Sets", f"{len(set_rows):,} rows"),
        ("", ""),
        ("Sheets", "Cards = every card. Sets = every set. Coverage = totals per language."),
        (
            "Finding a card",
            "Use the filter arrows on row 1 of the Cards sheet: filter Language, then "
            "Set Name (or Set Code), then Card Number.",
        ),
        (
            "Card Number",
            "The number exactly as printed on the card, including any prefix "
            "(001, TG12, SWSH284). 'Cards In Set' is the printed set size, so a card "
            "numbered above it is a secret rare.",
        ),
        (
            "Set Name (EN)",
            "English name for sets printed in Japanese, Chinese, Korean and Thai, where "
            "a translation is known.",
        ),
        (
            "Updating",
            "Run `python -m pokedb update` (or the Update Database GitHub Action) to "
            "rebuild this file from the latest data. The file is overwritten each time, "
            "so keep corrections in the source spreadsheets, not here.",
        ),
    ]
    for label, value in notes:
        about.append([label, value])
    about["A1"].font = Font(bold=True, size=14)
    for row in about.iter_rows(min_row=2, min_col=1, max_col=1):
        row[0].font = Font(bold=True)
    for row in about.iter_rows(min_row=2, min_col=2, max_col=2):
        row[0].alignment = Alignment(wrap_text=True, vertical="top")

    workbook.save(path)
    return path
