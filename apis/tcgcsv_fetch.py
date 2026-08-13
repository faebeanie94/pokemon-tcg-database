#!/usr/bin/env python3
"""Fetch TCGCSV (TCGplayer catalog mirror) into ``data/raw/tcgcsv/<game>/``.

Downloads groups + products (with extendedData for number/rarity) for the
configured TCGplayer categories. No API key required.

Games covered (see ``pokedb.config.TCGCSV_CATEGORIES`` / ``TCGCSV_GAMES``):

    mtg, yugioh, weiss, dbz, dbs, dbsfw, fleshblood, onepiece, lorcana,
    metazoo, warhammer, dicemasters

Usage:
    python3 apis/tcgcsv_fetch.py
    python3 apis/tcgcsv_fetch.py --game onepiece --game lorcana
    python3 apis/tcgcsv_fetch.py --category 68
    python3 apis/tcgcsv_fetch.py --delay 1.0

Rate-limit politely (default 0.35s between group requests; use ``--delay 1``
for ~1 req/s). Output is English-market TCGplayer data only — "all languages"
is **not** satisfied here; pair with Scryfall / YGOPRODeck / etc. for other
languages. See docs/DATA_SOURCES.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pokedb.config import TCGCSV_CATEGORIES, TCGCSV_GAMES  # noqa: E402
from pokedb.fetch_tcgcsv import fetch_all, fetch_game  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--game",
        action="append",
        choices=sorted(TCGCSV_CATEGORIES),
        help="limit to specific games (repeatable; default: all TCGCSV categories)",
    )
    parser.add_argument(
        "--category",
        action="append",
        type=int,
        help="raw TCGplayer categoryId (repeatable; resolved via TCGCSV_GAMES)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.35,
        help="seconds between product-group requests (default 0.35; ~1.0 for 1 req/s)",
    )
    args = parser.parse_args(argv)

    games: list[str] = list(args.game or [])
    for category_id in args.category or []:
        game = TCGCSV_GAMES.get(category_id)
        if game is None:
            print(f"Unknown TCGCSV categoryId: {category_id}", file=sys.stderr)
            print(f"Known: {dict(sorted(TCGCSV_GAMES.items()))}", file=sys.stderr)
            return 1
        if game not in games:
            games.append(game)

    if games:
        for game in games:
            print(f"TCGCSV {game} (category {TCGCSV_CATEGORIES[game]})...")
            count = fetch_game(game, delay=args.delay)
            print(f"  {count} products")
    else:
        print("Fetching all TCGCSV categories...")
        counts = fetch_all(None, delay=args.delay)
        for game, count in counts.items():
            print(f"  {game}: {count} products")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
