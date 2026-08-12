#!/usr/bin/env python3
"""
Export Pokémon card catalog data (name, set, number, rarity — no pricing)
from the PokéWallet API into an Excel workbook.

PokéWallet's free tier is limited to 100 requests/hour and 1,000/day.
This script tracks the rate limit headers on every response and
automatically pauses when you're close to the hourly cap, so it can run
unattended, but pulling a large catalog WILL take multiple runs/hours
on the free plan. Progress is checkpointed so you can stop and resume.

Usage:
    python3 pokewallet_export.py

Before running, paste your API key into API_KEY below.

Output:
    pokewallet_cards.xlsx
"""

import time
import json
import os
import requests
import pandas as pd

# ---- Config --------------------------------------------------------

API_KEY = "pk_live_43f78861d1653b8c2cbc8e89383d97dda01ebe376dfec641"  # <-- paste your pk_live_... key here
BASE_URL = "https://api.pokewallet.io"
OUTPUT_FILE = "pokewallet_cards.xlsx"
CHECKPOINT_FILE = "pokewallet_checkpoint.json"  # tracks which sets are already done
PAGE_LIMIT = 200          # max allowed per page
RETRY_COUNT = 5
REQUEST_TIMEOUT = 30

# How many requests to leave as a safety buffer before the hourly cap.
# If remaining requests drop to this or below, the script sleeps until the
# hour rolls over rather than risking a 429.
SAFETY_BUFFER = 3

session = requests.Session()
session.headers.update({"X-API-Key": API_KEY})


def request_with_rate_limit(url, params=None):
    """GET a URL, respecting PokéWallet's hourly/daily rate limit headers."""
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            print(f"  [warn] {e}, retry {attempt}/{RETRY_COUNT}")
            time.sleep(5)
            continue

        remaining_hour = resp.headers.get("X-RateLimit-Remaining-Hour")
        remaining_day = resp.headers.get("X-RateLimit-Remaining-Day")

        if resp.status_code == 429:
            print("  [rate limited] sleeping 60 minutes before retrying...")
            time.sleep(60 * 60)
            continue

        if resp.status_code == 200:
            # proactively slow down if we're close to the hourly cap
            if remaining_hour is not None and int(remaining_hour) <= SAFETY_BUFFER:
                print(f"  [rate guard] only {remaining_hour} requests left this hour, "
                      f"sleeping 60 minutes to let it reset...")
                time.sleep(60 * 60)
            if remaining_day is not None and int(remaining_day) <= SAFETY_BUFFER:
                print(f"  [rate guard] only {remaining_day} requests left today, "
                      f"sleeping 60 minutes and re-checking...")
                time.sleep(60 * 60)
            return resp.json()

        if resp.status_code in (500, 502, 503, 504):
            print(f"  [server error {resp.status_code}], retry {attempt}/{RETRY_COUNT}")
            time.sleep(10)
            continue

        # 400/401/404/etc — not retryable
        print(f"  [error] status {resp.status_code} on {url}: {resp.text[:200]}")
        return None

    print(f"  [error] giving up on {url}")
    return None


def flatten_card(card, set_language):
    info = card.get("card_info", {}) or {}
    return {
        "id": card.get("id"),
        "name": info.get("name"),
        "clean_name": info.get("clean_name"),
        "set_name": info.get("set_name"),
        "set_code": info.get("set_code"),
        "card_number": info.get("card_number"),
        "rarity": info.get("rarity"),
        "card_type": info.get("card_type"),
        "stage": info.get("stage"),
        "set_language": set_language,
        "image_languages": ", ".join((card.get("images") or {}).get("languages", []) or []),
    }


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return set(json.load(f))
    return set()


def save_checkpoint(done_set_ids):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(sorted(done_set_ids), f)


def load_existing_rows():
    if os.path.exists(OUTPUT_FILE):
        try:
            return pd.read_excel(OUTPUT_FILE).to_dict("records")
        except Exception:
            return []
    return []


def fetch_all_cards_for_set(set_id, set_code, set_language):
    """Paginate through every card in a set."""
    rows = []
    page = 1
    while True:
        url = f"{BASE_URL}/sets/{set_id}"
        data = request_with_rate_limit(url, params={"page": page, "limit": PAGE_LIMIT})
        if not data:
            break
        if data.get("disambiguation"):
            print(f"  [warn] set {set_id} ({set_code}) returned disambiguation, skipping")
            break

        cards = data.get("cards", [])
        rows.extend(flatten_card(c, set_language) for c in cards)

        total_cards = (data.get("set") or {}).get("total_cards", len(cards))
        if page * PAGE_LIMIT >= total_cards or not cards:
            break
        page += 1

    return rows


def main():
    if not API_KEY:
        print("Please paste your PokéWallet API key into API_KEY at the top of this script.")
        return

    print("Fetching set list...")
    sets_data = request_with_rate_limit(f"{BASE_URL}/sets")
    if not sets_data:
        print("Could not fetch the set list. Check your API key and connection.")
        return

    all_sets = sets_data.get("data", [])
    print(f"Found {len(all_sets)} sets total")

    done_set_ids = load_checkpoint()
    all_rows = load_existing_rows()
    if done_set_ids:
        print(f"Resuming: {len(done_set_ids)} sets already completed in a previous run, "
              f"{len(all_rows)} cards already collected")

    for i, s in enumerate(all_sets, start=1):
        set_id = s.get("set_id")
        set_code = s.get("set_code")
        set_language = s.get("language")

        if set_id in done_set_ids:
            continue

        print(f"[{i}/{len(all_sets)}] Fetching set {set_code or set_id} "
              f"({s.get('name')}, {s.get('card_count')} cards)...")
        rows = fetch_all_cards_for_set(set_id, set_code, set_language)
        all_rows.extend(rows)
        done_set_ids.add(set_id)

        # checkpoint after every set so a stop/rate-limit pause never loses progress
        save_checkpoint(done_set_ids)
        pd.DataFrame(all_rows).to_excel(OUTPUT_FILE, index=False, engine="openpyxl")

    print(f"\nDone. {len(all_rows)} total cards saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
