#!/usr/bin/env python3
"""
Export a TCGPlayer category via TCGCSV into an Excel workbook.

No API key required. Categories are listed at https://tcgcsv.com/tcgplayer/categories

Usage:
    python3 tcgcsv_export.py --game onepiece
    python3 tcgcsv_export.py --category 68 --out onepiece_cards.xlsx

Known game aliases (see pokedb.config.TCGCSV_CATEGORIES):
    mtg, yugioh, weiss, dbz, dbs, fleshblood, onepiece, lorcana,
    metazoo, warhammer, dicemasters, dbsfw
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

# Allow running from repo root without installing the package.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pokedb.config import TCGCSV_API, TCGCSV_CATEGORIES  # noqa: E402


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def results(payload):
    if isinstance(payload, dict):
        return payload.get("results", payload)
    return payload


def extended_map(product: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in product.get("extendedData") or []:
        name = str(item.get("name") or "").strip().lower()
        value = item.get("value")
        if name and value is not None:
            out[name] = str(value).strip()
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", choices=sorted(TCGCSV_CATEGORIES), help="game alias")
    parser.add_argument("--category", type=int, help="raw TCGplayer categoryId")
    parser.add_argument("--out", help="output xlsx path")
    parser.add_argument("--delay", type=float, default=0.35)
    args = parser.parse_args()

    if args.game:
        category_id = TCGCSV_CATEGORIES[args.game]
        label = args.game
    elif args.category:
        category_id = args.category
        label = str(category_id)
    else:
        parser.error("provide --game or --category")

    out = Path(args.out or f"tcgcsv_{label}_cards.xlsx")
    print(f"Fetching category {category_id}...")
    groups = results(get_json(f"{TCGCSV_API}/{category_id}/groups"))
    rows = []
    for group in groups:
        group_id = group["groupId"]
        set_name = group.get("name")
        time.sleep(args.delay)
        products = results(get_json(f"{TCGCSV_API}/{category_id}/{group_id}/products"))
        for product in products:
            ext = extended_map(product)
            rows.append(
                {
                    "game": label,
                    "group_id": group_id,
                    "set_name": set_name,
                    "set_abbreviation": group.get("abbreviation"),
                    "product_id": product.get("productId"),
                    "name": product.get("name"),
                    "number": ext.get("number") or ext.get("card number"),
                    "rarity": ext.get("rarity"),
                    "image_url": product.get("imageUrl"),
                }
            )
        print(f"  {set_name}: {len(products)} products")

    pd.DataFrame(rows).to_excel(out, index=False)
    print(f"Wrote {len(rows)} rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
