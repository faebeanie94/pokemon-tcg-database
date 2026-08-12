#!/usr/bin/env python3
"""
Export all English Pokémon cards (name, set, number, rarity, artist, images)
from the pokemontcg.io API into an Excel workbook.

Usage:
    python3 pokemontcgio_export.py

Before running, put your free API key below (get one at https://dev.pokemontcg.io)
or leave it blank to run unauthenticated (much slower / lower rate limits).

Output:
    pokemontcgio_cards.xlsx
"""

import time
import requests
import pandas as pd

# ---- Config ------------------------------------------------------------

API_KEY = "f7767675-e2f3-4fef-aded-d56e36f3b57e"  # <-- paste your free key here, or leave blank (strongly recommended: 500/502s are far more common unauthenticated)
BASE_URL = "https://api.pokemontcg.io/v2/cards"
PAGE_SIZE = 50            # smaller pages = lighter load on their flaky backend (was 100)
OUTPUT_FILE = "pokemontcgio_cards.xlsx"
RETRY_COUNT = 8           # more retries, since 500/502 here are often transient
BASE_RETRY_DELAY = 3      # seconds, doubles each retry (exponential backoff)
REQUEST_TIMEOUT = 60      # seconds
PACE_DELAY = 1.0          # seconds to wait before every request, success or not

session = requests.Session()
session.headers.update({"User-Agent": "tcgdatabase-export/1.0"})
if API_KEY:
    session.headers.update({"X-Api-Key": API_KEY})


def fetch_page(page):
    params = {"page": page, "pageSize": PAGE_SIZE}
    for attempt in range(1, RETRY_COUNT + 1):
        time.sleep(PACE_DELAY)  # pace every attempt, not just retries
        try:
            resp = session.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait = BASE_RETRY_DELAY * (2 ** attempt)
                print(f"  [rate limited] page {page}, waiting {wait}s before retry {attempt}/{RETRY_COUNT}")
                time.sleep(wait)
            elif resp.status_code in (500, 502, 503, 504):
                wait = BASE_RETRY_DELAY * (2 ** (attempt - 1))
                print(f"  [server error {resp.status_code}] page {page}, waiting {wait}s before retry {attempt}/{RETRY_COUNT}")
                time.sleep(wait)
            else:
                print(f"  [warn] status {resp.status_code} on page {page}, retry {attempt}/{RETRY_COUNT}")
                time.sleep(BASE_RETRY_DELAY)
        except requests.RequestException as e:
            wait = BASE_RETRY_DELAY * (2 ** (attempt - 1))
            print(f"  [warn] {e} on page {page}, waiting {wait}s before retry {attempt}/{RETRY_COUNT}")
            time.sleep(wait)
    print(f"  [error] giving up on page {page} after {RETRY_COUNT} attempts")
    return None


def flatten_card(card):
    """Pull out the fields most useful for a grading database (no pricing)."""
    return {
        "id": card.get("id"),
        "name": card.get("name"),
        "number": card.get("number"),
        "set_name": (card.get("set") or {}).get("name"),
        "set_series": (card.get("set") or {}).get("series"),
        "release_date": (card.get("set") or {}).get("releaseDate"),
        "rarity": card.get("rarity"),
        "supertype": card.get("supertype"),
        "subtypes": ", ".join(card.get("subtypes", []) or []),
        "artist": card.get("artist"),
        "image_small": (card.get("images") or {}).get("small"),
        "image_large": (card.get("images") or {}).get("large"),
    }


def main():
    print("Fetching page 1 to find total count...")
    first = fetch_page(1)
    if not first:
        print("Could not reach the API. Check your connection or API key.")
        return

    total_count = first.get("totalCount", 0)
    total_pages = (total_count // PAGE_SIZE) + (1 if total_count % PAGE_SIZE else 0)
    print(f"Total cards: {total_count} across {total_pages} pages")

    all_rows = [flatten_card(c) for c in first.get("data", [])]
    failed_pages = []

    for page in range(2, total_pages + 1):
        print(f"Fetching page {page}/{total_pages}...")
        data = fetch_page(page)
        if not data:
            failed_pages.append(page)
            continue
        all_rows.extend(flatten_card(c) for c in data.get("data", []))
        time.sleep(0.5)  # be polite between requests, reduces 500/502 frequency

        # checkpoint every 10 pages so a late failure doesn't lose earlier progress
        if page % 10 == 0:
            pd.DataFrame(all_rows).to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
            print(f"  [checkpoint] saved {len(all_rows)} cards so far")

    print(f"\nTotal cards collected: {len(all_rows)}")
    if failed_pages:
        print(f"Pages that failed after all retries: {failed_pages}")
        print("You can re-run the script later, or edit it to only re-fetch these pages.")

    df = pd.DataFrame(all_rows)
    df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
