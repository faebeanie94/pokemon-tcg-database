"""Fetch Lorcast sets and cards into ``data/raw/lorcast/``."""

from __future__ import annotations

import json
import urllib.request

from .config import LORCAST_API, LORCAST_RAW


def _get(url: str):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all() -> int:
    LORCAST_RAW.mkdir(parents=True, exist_ok=True)
    sets = _get(f"{LORCAST_API}/sets")
    if isinstance(sets, dict):
        sets = sets.get("results") or sets.get("data") or []
    (LORCAST_RAW / "sets.json").write_text(json.dumps(sets, ensure_ascii=False), encoding="utf-8")

    total = 0
    for set_payload in sets:
        code = set_payload.get("code") or set_payload.get("id")
        if not code:
            continue
        cards = _get(f"{LORCAST_API}/sets/{code}/cards")
        if isinstance(cards, dict):
            cards = cards.get("results") or cards.get("data") or cards.get("cards") or []
        (LORCAST_RAW / f"cards_{code}.json").write_text(
            json.dumps(cards, ensure_ascii=False), encoding="utf-8"
        )
        total += len(cards)
    return total
