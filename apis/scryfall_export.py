#!/usr/bin/env python3
"""
Download Scryfall bulk card data (all languages by default) to a local file.

Usage:
    python3 scryfall_export.py
    python3 scryfall_export.py --type default_cards --out mtg_default.jsonl

Bulk types: all_cards (multilingual), default_cards (English-centric), oracle_cards
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pokedb.config import SCRYFALL_API  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", default="all_cards", help="Scryfall bulk type")
    parser.add_argument("--out", help="output path (.jsonl or .jsonl.gz)")
    args = parser.parse_args()

    with urllib.request.urlopen(f"{SCRYFALL_API}/bulk-data", timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    entry = next(
        (item for item in payload.get("data", []) if item.get("type") == args.type),
        None,
    )
    if entry is None:
        print(f"Bulk type '{args.type}' not found", file=sys.stderr)
        return 1

    download_uri = entry["download_uri"]
    suffix = ".jsonl.gz" if download_uri.endswith(".gz") else ".jsonl"
    out = Path(args.out or f"scryfall_{args.type}{suffix}")
    print(f"Downloading {args.type} -> {out}")
    urllib.request.urlretrieve(download_uri, out)
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
