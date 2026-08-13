"""Fetch Flesh and Blood catalog from GoAgain."""

from __future__ import annotations

import json
import urllib.request

from .config import GOAGAIN_API, GOAGAIN_RAW


def _get(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all() -> dict[str, int]:
    GOAGAIN_RAW.mkdir(parents=True, exist_ok=True)
    sets = _get(f"{GOAGAIN_API}/sets")
    cards = _get(f"{GOAGAIN_API}/cards?limit=10000")
    if isinstance(sets, dict):
        sets = sets.get("data") or sets.get("results") or []
    if isinstance(cards, dict):
        cards = cards.get("data") or cards.get("results") or []
    (GOAGAIN_RAW / "sets.json").write_text(json.dumps(sets, ensure_ascii=False), encoding="utf-8")
    (GOAGAIN_RAW / "cards.json").write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")
    return {"sets": len(sets), "cards": len(cards)}
