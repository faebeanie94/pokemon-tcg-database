#!/usr/bin/env python3
"""
Export all Pokémon TCG cards (basic info) from the TCGdex API
for every supported language into a single Excel workbook,
one sheet per language. Non-English sheets get an extra
'english_name' column matched by card ID.

Usage (in Terminal):
    python3 tcgdex_export.py

Output:
    tcgdex_cards.xlsx  (in the same folder as this script)
"""

import time
import sys
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


def fetch_set_cards(lang, set_id, set_name, series_name):
    """Fetch one set's detail (includes the brief card list) and flatten it."""
    url = f"{BASE_URL}/{lang}/sets/{set_id}"
    data = fetch_json(url)
    if not data:
        return []

    cards = data.get("cards", [])
    rows = []
    for card in cards:
        row = dict(card)  # whatever fields TCGdex gives us (id, localId, name, image, rarity, etc.)
        row["set_id"] = set_id
        row["set_name"] = set_name
        row["series_name"] = series_name
        rows.append(row)
    return rows


def export_language(lang, label):
    print(f"\n=== {label} ({lang}) ===")
    sets_url = f"{BASE_URL}/{lang}/sets"
    sets = fetch_json(sets_url) or []
    print(f"  Found {len(sets)} sets")

    all_rows = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(
                fetch_set_cards,
                lang,
                s["id"],
                s.get("name", ""),
                s.get("serie", {}).get("name", "") if isinstance(s.get("serie"), dict) else "",
            ): s
            for s in sets
        }
        done = 0
        for fut in as_completed(futures):
            rows = fut.result()
            all_rows.extend(rows)
            done += 1
            if done % 20 == 0 or done == len(sets):
                print(f"  ...{done}/{len(sets)} sets processed, {len(all_rows)} cards so far")

    print(f"  Total cards for {label}: {len(all_rows)}")
    return all_rows


def main():
    english_names = {}  # card id -> English name, used to annotate other languages

    # process English first so the lookup is ready before other languages need it
    ordered_languages = sorted(LANGUAGES.items(), key=lambda item: item[0] != "en")

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        for lang, label in ordered_languages:
            rows = export_language(lang, label)
            if not rows:
                print(f"  [warn] no data for {label}, skipping sheet")
                continue

            if lang == "en":
                # build the lookup while we have English in hand
                for row in rows:
                    if row.get("id"):
                        english_names[row["id"]] = row.get("name", "")
            else:
                # attach the English name for the same card id, if we have it
                for row in rows:
                    row["english_name"] = english_names.get(row.get("id"), "")

            df = pd.json_normalize(rows)

            # Put the most useful columns first if they exist
            preferred_order = [
                "set_name", "series_name", "localId", "id", "name",
                "english_name", "rarity", "category", "image",
            ]
            cols = [c for c in preferred_order if c in df.columns]
            cols += [c for c in df.columns if c not in cols]
            df = df[cols]

            sheet_name = label[:31]  # Excel sheet name limit
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"\nDone. Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
