#!/usr/bin/env python3
"""Write the curated sports spine workbooks into sources/.

Creates:
  sources/sports_database.xlsx  — set spine (season, manufacturer, sport, …)
  sources/sports_cards.xlsx     — checklist rows for the two grading examples

Run from the repo root:

    python3 scripts/seed_sports_xlsx.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from openpyxl import Workbook  # noqa: E402

SOURCES = ROOT / "sources"

SETS = [
    {
        "season": "2025-26",
        "manufacturer": "Topps",
        "sport": "soccer",
        "set_name": "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
        "release_date": "2025-09-01",
        "source_set_id": "2025-26-topps-manchester-united-team-set",
        "language": "en",
    },
    {
        "season": "2024",
        "manufacturer": "Panini",
        "sport": "wrestling",
        "set_name": "2024 PANINI FLAWLESS WWE",
        "release_date": "2024-11-15",
        "source_set_id": "2024-panini-flawless-wwe",
        "language": "en",
    },
]

CARDS = [
    {
        "set_id": "2025-26-topps-manchester-united-team-set",
        "set_name": "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
        "number": "38",
        "subject": "SIR DAVID BECKHAM",
        "parallel": "",
        "variant_tags": "",
        "serial_number": "",
        "serial_total": "",
        "display_name": "SIR DAVID BECKHAM",
    },
    {
        "set_id": "2025-26-topps-manchester-united-team-set",
        "set_name": "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
        "number": "38",
        "subject": "SIR DAVID BECKHAM",
        "parallel": "HALO REF",
        "variant_tags": "",
        "serial_number": "",
        "serial_total": "",
        "display_name": "SIR DAVID BECKHAM - HALO REF.",
    },
    {
        "set_id": "2024-panini-flawless-wwe",
        "set_name": "2024 PANINI FLAWLESS WWE",
        "number": "SSL-SM",
        "subject": "SHAWN MICHAELS",
        "parallel": "",
        "variant_tags": "",
        "serial_number": "",
        "serial_total": "",
        "display_name": "SHAWN MICHAELS",
    },
    {
        "set_id": "2024-panini-flawless-wwe",
        "set_name": "2024 PANINI FLAWLESS WWE",
        "number": "SSL-SM",
        "subject": "SHAWN MICHAELS",
        "parallel": "RUBY REF",
        "variant_tags": "AUTO",
        "serial_number": "09",
        "serial_total": "15",
        "display_name": "SHAWN MICHAELS – AUTO - RUBY REF. – 09/15",
    },
]


def _write(path: Path, headers: list[str], rows: list[dict]) -> None:
    book = Workbook()
    sheet = book.active
    sheet.title = "Sheet1"
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header, "") for header in headers])
    path.parent.mkdir(parents=True, exist_ok=True)
    book.save(path)
    print(f"wrote {path} ({len(rows)} rows)")


def main() -> int:
    _write(
        SOURCES / "sports_database.xlsx",
        ["season", "manufacturer", "sport", "set_name", "release_date", "source_set_id", "language"],
        SETS,
    )
    _write(
        SOURCES / "sports_cards.xlsx",
        [
            "set_id",
            "set_name",
            "number",
            "subject",
            "parallel",
            "variant_tags",
            "serial_number",
            "serial_total",
            "display_name",
        ],
        CARDS,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
