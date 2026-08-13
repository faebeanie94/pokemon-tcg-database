"""Download TCGCSV (TCGplayer catalog mirror) into ``data/raw/tcgcsv/<game>/``."""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Iterable

from .config import TCGCSV_API, TCGCSV_CATEGORIES, TCGCSV_RAW


def _get_json(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_game(game: str, *, delay: float = 0.35) -> int:
    category_id = TCGCSV_CATEGORIES[game]
    out = TCGCSV_RAW / game
    out.mkdir(parents=True, exist_ok=True)

    groups_payload = _get_json(f"{TCGCSV_API}/{category_id}/groups")
    groups = groups_payload.get("results", groups_payload) if isinstance(groups_payload, dict) else groups_payload
    (out / "groups.json").write_text(json.dumps(groups, ensure_ascii=False), encoding="utf-8")

    product_count = 0
    for group in groups:
        group_id = group["groupId"]
        time.sleep(delay)
        products_payload = _get_json(f"{TCGCSV_API}/{category_id}/{group_id}/products")
        products = (
            products_payload.get("results", products_payload)
            if isinstance(products_payload, dict)
            else products_payload
        )
        (out / f"products_{group_id}.json").write_text(
            json.dumps(products, ensure_ascii=False), encoding="utf-8"
        )
        product_count += len(products)
    return product_count


def fetch_all(games: Iterable[str] | None = None) -> dict[str, int]:
    selected = list(games) if games else list(TCGCSV_CATEGORIES)
    unknown = [game for game in selected if game not in TCGCSV_CATEGORIES]
    if unknown:
        raise SystemExit(f"Unknown TCGCSV games: {', '.join(unknown)}")

    counts: dict[str, int] = {}
    for game in selected:
        print(f"  TCGCSV {game} (category {TCGCSV_CATEGORIES[game]})...")
        counts[game] = fetch_game(game)
        print(f"    {counts[game]} products")
    return counts
