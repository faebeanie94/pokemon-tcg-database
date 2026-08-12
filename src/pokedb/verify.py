"""Cross-check the supplied spreadsheets against the live API data.

``tcgdex_cards.xlsx`` is an earlier export of the same TCGdex data the fetcher
downloads. It is not ingested (it would only duplicate rows), but comparing it
catches the case where the API silently drops or renames cards.
"""

from __future__ import annotations

import json

from .config import TCGDEX_RAW
from .sources._excel import find_source_file, language_from_text, read_sheets

TCGDEX_EXPORT = "tcgdex_cards.xlsx"


def verify() -> bool:
    path = find_source_file(TCGDEX_EXPORT)
    if path is None:
        print(f"{TCGDEX_EXPORT} not found - nothing to verify")
        return True

    ok = True
    for sheet_name, frame in read_sheets(path):
        language = language_from_text(sheet_name)
        if language is None:
            print(f"  ? {sheet_name}: cannot tell which language this sheet is")
            continue
        raw_file = TCGDEX_RAW / f"{language}.json"
        if not raw_file.exists():
            print(f"  ? {sheet_name}: no downloaded data for '{language}'")
            continue

        payload = json.loads(raw_file.read_text(encoding="utf-8"))
        api_ids = {
            card["id"]
            for set_payload in payload["sets"].values()
            for card in (set_payload.get("cards") or [])
        }
        sheet_ids = {str(value) for value in frame["id"].dropna()} if "id" in frame else set()
        only_sheet = sheet_ids - api_ids
        only_api = api_ids - sheet_ids

        status = "OK " if not only_sheet else "!! "
        ok = ok and not only_sheet
        print(
            f"  {status}{sheet_name:<22} {language:<6} spreadsheet={len(sheet_ids):>6} "
            f"api={len(api_ids):>6} missing_from_api={len(only_sheet):>4} "
            f"new_in_api={len(only_api):>4}"
        )
        for card_id in sorted(only_sheet)[:5]:
            print(f"      only in spreadsheet: {card_id}")
    return ok
