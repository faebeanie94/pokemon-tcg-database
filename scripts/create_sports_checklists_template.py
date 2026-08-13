#!/usr/bin/env python3
"""Write a blank ``sources/sports_checklists.xlsx`` matching the loader columns.

Operators append checklist rows here (or use sports_database.xlsx +
sports_cards.xlsx). The loader is ``src/pokedb/sources/sports_xlsx.py``.

    python3 scripts/create_sports_checklists_template.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from openpyxl import Workbook  # noqa: E402

OUT = ROOT / "sources" / "sports_checklists.xlsx"

HEADERS = [
    "manufacturer",
    "sport",
    "season",
    "set_name",
    "set_id",
    "subject_name",
    "parallel",
    "notations",
    "number",
    "serial_number",
    "print_run",
    "display_name",
    "language",
    "release_date",
]

# One commented-style example row operators can overwrite.
EXAMPLE = [
    "Topps",
    "soccer",
    "2025-26",
    "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
    "2025-26-topps-manchester-united-team-set",
    "SIR DAVID BECKHAM",
    "HALO REF",
    "",
    "38",
    "",
    "",
    "SIR DAVID BECKHAM - HALO REF.",
    "en",
    "2025-09-01",
]


def main() -> int:
    book = Workbook()
    sheet = book.active
    sheet.title = "checklists"
    sheet.append(HEADERS)
    sheet.append(EXAMPLE)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    book.save(OUT)
    print(f"wrote {OUT} (headers + 1 example row)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
