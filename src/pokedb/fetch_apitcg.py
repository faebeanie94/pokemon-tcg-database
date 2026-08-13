"""Fetch selected TCG catalogs from apitcg.com.

apitcg now requires an API key (register at https://apitcg.com/platform).
Set ``APITCG_API_KEY`` in the environment. Without a key this prints staging
help and exits successfully so ``pnpm refresh:games`` can continue.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .config import APITCG_API, APITCG_RAW

SLUGS = ("one-piece", "dragon-ball-fusion")
GAME_TO_SLUG = {
    "onepiece": "one-piece",
    "one-piece": "one-piece",
    "dbsfw": "dragon-ball-fusion",
    "dragon-ball-fusion": "dragon-ball-fusion",
}

_UA = "Mozilla/5.0 (compatible; pokedb/1.0; +https://github.com/)"
# Prefer www — bare apitcg.com 308-redirects and may drop auth headers.
_API = APITCG_API.replace("://apitcg.com", "://www.apitcg.com")


def _get(url: str, api_key: str):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _UA,
            "Accept": "application/json",
            "x-api-key": api_key,
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all(slugs: list[str] | None = None) -> dict[str, int]:
    api_key = (os.environ.get("APITCG_API_KEY") or "").strip()
    if not api_key:
        print(
            "  APITCG_API_KEY is not set — skipping live apitcg fetch.\n"
            "  Register at https://apitcg.com/platform, then re-run:\n"
            "    APITCG_API_KEY=… PYTHONPATH=src python3 -m pokedb fetch --source apitcg\n"
            "  Or drop sets.json/cards.json under data/raw/apitcg/<slug>/."
        )
        return {}

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
            sets = _get(f"{_API}/{slug}/sets", api_key)
        except Exception as exc:  # noqa: BLE001
            print(f"    sets fetch failed: {exc}")
            sets = []
        try:
            cards = _get(f"{_API}/{slug}/cards", api_key)
        except urllib.error.HTTPError as exc:
            print(f"    cards fetch failed: {exc}")
            cards = []
        except Exception as exc:  # noqa: BLE001
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
