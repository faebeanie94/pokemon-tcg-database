#!/usr/bin/env python3
"""
Export the Simplified Chinese Pokémon card catalog (metadata only, no
pricing) from the PikaQian API into an Excel workbook.

IMPORTANT — PikaQian's free tier is capped at 500 requests/MONTH (not per
hour). With ~13,000+ cards at up to 100 per page, a full export costs
roughly 130+ requests. That's affordable once, but re-running it casually
will burn through your monthly quota fast. This script checkpoints its
cursor position so an interrupted run can resume without starting over
and re-spending requests already used.

Usage:
    PIKAQIAN_API_KEY=pk_live_... python3 pikaqian_export.py

The API key is read from the PIKAQIAN_API_KEY environment variable. Never
hard-code it here — this file is committed to a public repository.

Output:
    pikaqian_cards.xlsx   (two sheets: "Cards" and "Sets")
"""

import time
import json
import os
import requests
import pandas as pd

# ---- Config --------------------------------------------------------

API_KEY = os.environ.get("PIKAQIAN_API_KEY", "")
BASE_URL = "https://api.pikaqian.com/v1"
OUTPUT_FILE = "pikaqian_cards.xlsx"
CHECKPOINT_FILE = "pikaqian_checkpoint.json"
PAGE_LIMIT = 100          # cards per page; reduces total request count
RETRY_COUNT = 5
REQUEST_TIMEOUT = 30

session = requests.Session()
session.headers.update({"X-API-Key": API_KEY})

request_count = 0  # tracked locally so you can see roughly what you spent this run


def api_get(path, params=None, allow_param_fallback=False):
    """GET a PikaQian endpoint, handling their error envelope and rate limits."""
    global request_count
    url = f"{BASE_URL}{path}"
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            print(f"  [warn] {e}, retry {attempt}/{RETRY_COUNT}")
            time.sleep(5)
            continue

        request_count += 1

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            wait = int(retry_after) if retry_after and retry_after.isdigit() else 60
            print(f"  [rate limited] waiting {wait}s before retry {attempt}/{RETRY_COUNT}")
            time.sleep(wait)
            continue

        if resp.status_code >= 500:
            print(f"  [server error {resp.status_code}], retry {attempt}/{RETRY_COUNT}")
            time.sleep(5)
            continue

        # 4xx other than 429
        try:
            err = resp.json().get("error", {})
            code = err.get("code")
            print(f"  [error {resp.status_code}] {code}: {err.get('message')}")
            # if an unknown query param caused this, drop it and retry once rather than aborting
            if allow_param_fallback and code == "unknown_query_param" and params and "page_size" in params:
                print("  [fallback] retrying without page_size param (server default page size)")
                retry_params = {k: v for k, v in params.items() if k != "page_size"}
                return api_get(path, params=retry_params, allow_param_fallback=False)
        except Exception:
            print(f"  [error {resp.status_code}] {resp.text[:200]}")
        return None

    print(f"  [error] giving up on {path}")
    return None


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"cursor": None, "done": False}


def save_checkpoint(cursor, done=False):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"cursor": cursor, "done": done}, f)


def load_existing_rows(sheet_name):
    if os.path.exists(OUTPUT_FILE):
        try:
            return pd.read_excel(OUTPUT_FILE, sheet_name=sheet_name).to_dict("records")
        except Exception:
            return []
    return []


def fetch_all_sets():
    print("Fetching sets...")
    data = api_get("/sets")
    if not data:
        return []
    sets = data.get("data", [])
    # follow cursor pagination if there happen to be many sets
    cursor = (data.get("pagination") or {}).get("next_cursor")
    while cursor:
        data = api_get("/sets", params={"cursor": cursor})
        if not data:
            break
        sets.extend(data.get("data", []))
        cursor = (data.get("pagination") or {}).get("next_cursor")
    print(f"  Found {len(sets)} sets")
    return sets


def fetch_all_cards(resume_cursor=None):
    checkpoint = load_checkpoint()
    if checkpoint.get("done"):
        print("Checkpoint says a previous run already finished. "
              f"Delete {CHECKPOINT_FILE} to force a fresh export.")
        return load_existing_rows("Cards")

    cursor = resume_cursor if resume_cursor is not None else checkpoint.get("cursor")
    all_rows = load_existing_rows("Cards")
    if cursor:
        print(f"Resuming from saved cursor, {len(all_rows)} cards already collected")

    page = 0
    while True:
        page += 1
        params = {"page_size": PAGE_LIMIT}
        if cursor:
            params["cursor"] = cursor

        print(f"Fetching card page {page} (requests used this run: {request_count})...")
        data = api_get("/cards", params=params, allow_param_fallback=True)
        if not data:
            print("Stopping due to a request failure. Progress is checkpointed — rerun to resume.")
            save_checkpoint(cursor, done=False)
            break

        cards = data.get("data", [])
        all_rows.extend(cards)

        cursor = (data.get("pagination") or {}).get("next_cursor")
        save_checkpoint(cursor, done=(cursor is None))

        # periodic save so interruptions don't lose progress
        if page % 5 == 0:
            pd.DataFrame(all_rows).to_excel(OUTPUT_FILE, sheet_name="Cards", index=False)
            print(f"  [checkpoint] saved {len(all_rows)} cards so far")

        if not cursor:
            print("Reached the end of the card catalog.")
            break

    return all_rows


def main():
    if not API_KEY:
        print("Set PIKAQIAN_API_KEY in your environment before running this script.")
        return

    sets = fetch_all_sets()
    cards = fetch_all_cards()

    print(f"\nTotal cards collected: {len(cards)}")
    print(f"Total requests used this run: {request_count} "
          f"(free tier allows 500/month total)")

    cards_df = pd.json_normalize(cards) if cards else pd.DataFrame()
    sets_df = pd.json_normalize(sets) if sets else pd.DataFrame()

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        if not cards_df.empty:
            # put the most useful columns first if present
            preferred = ["set_id", "card_number", "name", "local_name",
                         "rarity", "rarity_label", "card_type", "element", "variant"]
            cols = [c for c in preferred if c in cards_df.columns]
            cols += [c for c in cards_df.columns if c not in cols]
            cards_df = cards_df[cols]
        cards_df.to_excel(writer, sheet_name="Cards", index=False)
        sets_df.to_excel(writer, sheet_name="Sets", index=False)

    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
