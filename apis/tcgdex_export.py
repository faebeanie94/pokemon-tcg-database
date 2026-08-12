#!/usr/bin/env python3
"""
Export the Pokémon TCG card catalog from the TCGdex API for every language
it serves, into a single Excel workbook: one sheet per language, plus a
"Sets" sheet holding set-level metadata for all languages.

TCGdex needs no API key. Languages that return no sets are skipped
automatically, so the LANGUAGES list can stay optimistic.

The columns are chosen for card *identification* (the fields a grader can
read off a physical card), not for gameplay data:

    language, set_id, set_name, set_abbreviation, series_name,
    printed_total, card_number, id, name, english_name

`id` is TCGdex's own card identifier. It keeps that name because
`python -m pokedb verify` reads this column to compare the workbook against a
fresh download.

`printed_total` is the denominator printed on the card ("4/102" -> 102),
which together with the number is often enough to pin down a set.

`english_name` is only populated for languages that share TCGdex card IDs
with English — the Western languages, which are translations of the same
physical sets. Japanese, Korean, Chinese, Indonesian and Thai releases are
separate sets with their own IDs, so no ID-based English link exists and the
column is left blank for them.

Usage:
    python3 tcgdex_export.py

Output:
    tcgdex_cards.xlsx  (in the current working directory)
"""

import time
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---- Config ----------------------------------------------------------

LANGUAGES = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "pt-br": "Portuguese (Brazil)",
    "pt-pt": "Portuguese (Portugal)",
    "de": "German",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh-tw": "Chinese (Traditional)",
    "zh-cn": "Chinese (Simplified)",
    "id": "Indonesian",
    "th": "Thai",
}

BASE_URL = "https://api.tcgdex.net/v2"
OUTPUT_FILE = "tcgdex_cards.xlsx"
MAX_WORKERS = 8          # parallel requests per language
RETRY_COUNT = 3
RETRY_DELAY = 2          # seconds

CARD_COLUMNS = [
    "language", "set_id", "set_name", "set_abbreviation", "series_name",
    "printed_total", "card_number", "id", "name", "english_name",
]

SET_COLUMNS = [
    "language", "set_id", "set_name", "set_abbreviation", "series_id",
    "series_name", "release_date", "printed_total", "card_count_total",
]

session = requests.Session()


def fetch_json(url):
    """GET a URL and return parsed JSON, with basic retry handling."""
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                return None
            else:
                print(f"  [warn] {resp.status_code} on {url}, retry {attempt}/{RETRY_COUNT}")
        except requests.RequestException as e:
            print(f"  [warn] {e} on {url}, retry {attempt}/{RETRY_COUNT}")
        time.sleep(RETRY_DELAY)
    print(f"  [error] giving up on {url}")
    return None


def fetch_set(lang, set_id):
    """Fetch one set's detail, which includes its brief card list.

    Returns (set_row, card_rows). The set detail carries the abbreviation,
    release date and printed total that the /sets summary leaves out.
    """
    data = fetch_json(f"{BASE_URL}/{lang}/sets/{set_id}")
    if not data:
        return None, []

    serie = data.get("serie") or {}
    abbreviation = data.get("abbreviation") or {}
    card_count = data.get("cardCount") or {}
    printed_total = card_count.get("official")

    set_row = {
        "language": lang,
        "set_id": data.get("id", set_id),
        "set_name": data.get("name", ""),
        "set_abbreviation": abbreviation.get("official", ""),
        "series_id": serie.get("id", ""),
        "series_name": serie.get("name", ""),
        "release_date": data.get("releaseDate", ""),
        "printed_total": printed_total,
        "card_count_total": card_count.get("total"),
    }

    card_rows = [
        {
            "language": lang,
            "set_id": set_row["set_id"],
            "set_name": set_row["set_name"],
            "set_abbreviation": set_row["set_abbreviation"],
            "series_name": set_row["series_name"],
            "printed_total": printed_total,
            "card_number": card.get("localId", ""),
            "id": card.get("id", ""),
            "name": card.get("name", ""),
            "english_name": "",
        }
        for card in data.get("cards", [])
    ]
    return set_row, card_rows


def export_language(lang, label):
    """Fetch every set and card for one language."""
    print(f"\n=== {label} ({lang}) ===")
    sets = fetch_json(f"{BASE_URL}/{lang}/sets") or []
    print(f"  Found {len(sets)} sets")
    if not sets:
        return [], []

    set_rows, card_rows = [], []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(fetch_set, lang, s["id"]) for s in sets if s.get("id")]
        done = 0
        for fut in as_completed(futures):
            set_row, cards = fut.result()
            if set_row:
                set_rows.append(set_row)
            card_rows.extend(cards)
            done += 1
            if done % 20 == 0 or done == len(futures):
                print(f"  ...{done}/{len(futures)} sets processed, {len(card_rows)} cards so far")

    print(f"  Total cards for {label}: {len(card_rows)}")
    return set_rows, card_rows


def main():
    english_names = {}   # card id -> English name, for the Western languages
    all_set_rows = []
    sheets = []          # (sheet_name, card_rows), written after Sets is built

    # English first so the name lookup is ready for the languages that share its IDs
    ordered = sorted(LANGUAGES.items(), key=lambda item: item[0] != "en")

    for lang, label in ordered:
        set_rows, card_rows = export_language(lang, label)
        all_set_rows.extend(set_rows)
        if not card_rows:
            print(f"  [skip] no data for {label}")
            continue

        if lang == "en":
            english_names = {
                r["id"]: r["name"] for r in card_rows if r.get("id")
            }
        else:
            matched = 0
            for row in card_rows:
                english = english_names.get(row["id"], "")
                row["english_name"] = english
                if english:
                    matched += 1
            print(f"  Linked {matched}/{len(card_rows)} cards to an English name")

        sheets.append((label[:31], card_rows))   # 31 chars is Excel's sheet name limit

    total = sum(len(rows) for _, rows in sheets)
    print(f"\nWriting {total} cards across {len(sheets)} languages to {OUTPUT_FILE}...")

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        pd.DataFrame(all_set_rows, columns=SET_COLUMNS).to_excel(
            writer, sheet_name="Sets", index=False
        )
        for sheet_name, rows in sheets:
            pd.DataFrame(rows, columns=CARD_COLUMNS).to_excel(
                writer, sheet_name=sheet_name, index=False
            )

    print(f"Done. {len(all_set_rows)} sets and {total} cards saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
