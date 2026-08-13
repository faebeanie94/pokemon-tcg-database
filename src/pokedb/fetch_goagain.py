"""Fetch Flesh and Blood catalog from GoAgain."""

from __future__ import annotations

import json
import urllib.request

from .config import GOAGAIN_API, GOAGAIN_RAW

_UA = "Mozilla/5.0 (compatible; pokedb/1.0; +https://github.com/)"
_PAGE = 100


def _get(url: str):
    req = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": _UA}
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_paged(path: str) -> list:
    """Walk offset/limit pages until all rows are collected."""
    offset = 0
    rows: list = []
    total: int | None = None
    while True:
        payload = _get(f"{GOAGAIN_API}{path}?limit={_PAGE}&offset={offset}")
        if isinstance(payload, list):
            rows.extend(payload)
            break
        batch = payload.get("data") or payload.get("results") or []
        rows.extend(batch)
        total = payload.get("total", total)
        if not batch:
            break
        offset += len(batch)
        if total is not None and offset >= int(total):
            break
        if len(batch) < _PAGE:
            break
    return rows


def fetch_all() -> dict[str, int]:
    GOAGAIN_RAW.mkdir(parents=True, exist_ok=True)
    sets = _fetch_paged("/v1/sets")
    cards = _fetch_paged("/v1/cards")
    (GOAGAIN_RAW / "sets.json").write_text(json.dumps(sets, ensure_ascii=False), encoding="utf-8")
    (GOAGAIN_RAW / "cards.json").write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")
    return {"sets": len(sets), "cards": len(cards)}
