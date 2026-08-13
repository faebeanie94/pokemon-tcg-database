"""Stage Japanese One Piece checklists from the Bandai JP cardlist.

English One Piece already comes from TCGCSV + apitcg. Bandai's official JP
cardlist (https://www.onepiece-cardgame.com/cardlist/) has no stable public
API — live HTML scraping is fragile and often blocked.

This module:

1. Prints how to drop a normalized dump under ``data/raw/bandai_onepiece/``
2. Optionally normalizes an operator-supplied ``--from-file`` JSON into that
   shape (same pattern as TCDB / Beckett adapters)

Expected dump shape (``sets.json`` + ``cards.json``, or one combined file)::

    {
      "sets": [{"id": "OP01", "name": "ROMANCE DAWN", "language": "ja"}],
      "cards": [{
        "set_id": "OP01",
        "number": "001",
        "name": "モンキー・D・ルフィ",
        "name_en": "Monkey.D.Luffy",
        "rarity": "L",
        "language": "ja"
      }]
    }
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import DATA_RAW

OUT_DIR = DATA_RAW / "bandai_onepiece"


def print_help() -> None:
    print(
        """
Bandai JP One Piece cardlist staging
====================================

English catalog: TCGCSV + apitcg (pnpm fetch:onepiece).
Japanese catalog: drop a normalized dump here, then rebuild:

  data/raw/bandai_onepiece/sets.json
  data/raw/bandai_onepiece/cards.json

Or normalize a hand-built / offline-scraped JSON:

  PYTHONPATH=src python3 -m pokedb.fetch_bandai_onepiece --from-file dump.json

Live HTML scrape of one piece-cardgame.com is not automated here (markup / ToS).
""".strip()
    )


def normalize(payload: dict) -> tuple[list[dict], list[dict]]:
    sets: list[dict] = []
    for item in payload.get("sets") or []:
        if not isinstance(item, dict):
            continue
        set_id = str(item.get("id") or item.get("set_id") or item.get("code") or "").strip()
        name = str(item.get("name") or item.get("set_name") or set_id).strip()
        if not set_id and not name:
            continue
        sets.append(
            {
                "id": set_id or name,
                "name": name or set_id,
                "name_en": (item.get("name_en") or "").strip() or None,
                "abbreviation": (item.get("abbreviation") or item.get("code") or set_id).strip()
                or None,
                "release_date": (item.get("release_date") or "").strip() or None,
                "language": (item.get("language") or "ja").strip() or "ja",
            }
        )

    cards: list[dict] = []
    for item in payload.get("cards") or []:
        if not isinstance(item, dict):
            continue
        set_id = str(item.get("set_id") or item.get("set") or "").strip()
        number = str(item.get("number") or item.get("card_number") or "").strip()
        name = str(item.get("name") or item.get("printed_name") or "").strip()
        if not set_id or not number or not name:
            continue
        cards.append(
            {
                "set_id": set_id,
                "number": number,
                "name": name,
                "name_en": (item.get("name_en") or "").strip() or None,
                "rarity": (item.get("rarity") or "").strip() or None,
                "image_url": (item.get("image_url") or item.get("image") or "").strip() or None,
                "language": (item.get("language") or "ja").strip() or "ja",
            }
        )
    return sets, cards


def write_dump(sets: list[dict], cards: list[dict]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "sets.json").write_text(
        json.dumps(sets, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "cards.json").write_text(
        json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return OUT_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-file", type=Path, help="operator JSON dump to normalize")
    args = parser.parse_args(argv)

    if args.from_file is None:
        print_help()
        return 0

    payload = json.loads(args.from_file.read_text(encoding="utf-8"))
    sets, cards = normalize(payload)
    path = write_dump(sets, cards)
    print(f"wrote {len(sets)} sets / {len(cards)} cards under {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
