"""Fetch Bandai Japanese One Piece cardlist into ``data/raw/bandai/onepiece/``.

The official site (https://www.onepiece-cardgame.com/cardlist/) is HTML-only.
This module writes a placeholder structure and documents the expected shape;
operators can drop scraped JSON into the same paths, or extend this fetcher.
"""

from __future__ import annotations

import json

from .config import DATA_RAW

RAW = DATA_RAW / "bandai" / "onepiece"
CARDLIST_URL = "https://www.onepiece-cardgame.com/cardlist/"


def fetch_all() -> dict[str, str]:
    RAW.mkdir(parents=True, exist_ok=True)
    meta = {
        "source": CARDLIST_URL,
        "note": (
            "Drop scraped sets.json / cards.json here. "
            "Automated HTML scrape is intentionally not bundled."
        ),
    }
    (RAW / "README.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  Bandai One Piece: wrote placeholder under {RAW}")
    print(f"    Scrape {CARDLIST_URL} into sets.json + cards.json to enable the loader.")
    return {"status": "placeholder"}
