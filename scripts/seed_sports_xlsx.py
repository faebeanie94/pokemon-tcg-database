#!/usr/bin/env python3
"""Write the curated sports spine workbooks into sources/.

Creates:
  sources/sports_database.xlsx  — set spine (season, manufacturer, sport, …)
  sources/sports_cards.xlsx     — checklist rows aligned with data/raw/sports/seed.json

Run from the repo root:

    python3 scripts/seed_sports_xlsx.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from openpyxl import Workbook  # noqa: E402

SOURCES = ROOT / "sources"
SEED = ROOT / "data" / "raw" / "sports" / "seed.json"


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
    payload = json.loads(SEED.read_text(encoding="utf-8"))
    sets = []
    for item in payload.get("sets") or []:
        sets.append(
            {
                "season": item.get("product_year") or "",
                "manufacturer": item.get("manufacturer") or "",
                "sport": item.get("sport") or "",
                "set_name": item.get("name") or "",
                "release_date": item.get("release_date") or "",
                "source_set_id": item.get("id") or "",
                "language": item.get("language") or "en",
            }
        )
    cards = []
    for item in payload.get("cards") or []:
        cards.append(
            {
                "set_id": item.get("set_id") or "",
                "set_name": "",
                "number": item.get("number") or "",
                "subject": item.get("subject_name") or "",
                "parallel": item.get("parallel") or "",
                "variant_tags": item.get("notations") or "",
                "serial_number": item.get("serial_number") or "",
                "serial_total": item.get("print_run") or "",
                "display_name": item.get("display_name") or item.get("name") or "",
            }
        )

    _write(
        SOURCES / "sports_database.xlsx",
        ["season", "manufacturer", "sport", "set_name", "release_date", "source_set_id", "language"],
        sets,
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
        cards,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
