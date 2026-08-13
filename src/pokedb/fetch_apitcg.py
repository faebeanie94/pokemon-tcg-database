"""Fetch selected TCG catalogs from apitcg.com."""

from __future__ import annotations

import json
import urllib.request

from .config import APITCG_API, APITCG_RAW

SLUGS = ("one-piece", "dragon-ball-fusion")
GAME_TO_SLUG = {
    "onepiece": "one-piece",
    "one-piece": "one-piece",
    "dbsfw": "dragon-ball-fusion",
    "dragon-ball-fusion": "dragon-ball-fusion",
}


def _get(url: str):
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all(slugs: list[str] | None = None) -> dict[str, int]:
    if slugs:
        selected = [GAME_TO_SLUG.get(item, item) for item in slugs]
        selected = [item for item in selected if item in SLUGS]
        if not selected:
            selected = list(SLUGS)
    else:
        selected = list(SLUGS)
    counts: dict[str, int] = {}
    for slug in selected:
        out = APITCG_RAW / slug
        out.mkdir(parents=True, exist_ok=True)
        print(f"  apitcg {slug}...")
        try:
            sets = _get(f"{APITCG_API}/{slug}/sets")
        except Exception:
            sets = []
        try:
            cards = _get(f"{APITCG_API}/{slug}/cards")
        except Exception as exc:
            print(f"    cards fetch failed: {exc}")
            cards = []
        if isinstance(sets, dict):
            sets = sets.get("data") or sets.get("results") or []
        if isinstance(cards, dict):
            cards = cards.get("data") or cards.get("results") or []
        (out / "sets.json").write_text(json.dumps(sets, ensure_ascii=False), encoding="utf-8")
        (out / "cards.json").write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")
        counts[slug] = len(cards)
        print(f"    {len(sets)} sets, {len(cards)} cards")
    return counts
