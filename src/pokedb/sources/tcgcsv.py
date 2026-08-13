"""Load TCGCSV nightly dumps (TCGplayer catalog mirror).

Expects ``data/raw/tcgcsv/<game>/groups.json`` and per-group
``products_<groupId>.json`` written by ``fetch_tcgcsv``.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import TCGCSV_CATEGORIES, TCGCSV_RAW
from ..normalize import clean_text, parse_date
from ..records import CardRecord, SetRecord, SourceData
from ._tcgplayer import extended_map, pick_number, pick_rarity

SOURCE = "tcgcsv"


def load() -> SourceData | None:
    if not TCGCSV_RAW.exists():
        return None

    data = SourceData(name=SOURCE)
    found = False

    for game in TCGCSV_CATEGORIES:
        game_dir = TCGCSV_RAW / game
        groups_file = game_dir / "groups.json"
        if not groups_file.exists():
            continue
        found = True
        groups = json.loads(groups_file.read_text(encoding="utf-8"))
        for group in groups:
            group_id = str(group["groupId"])
            set_name = clean_text(group.get("name")) or group_id
            abbreviation = clean_text(group.get("abbreviation"))
            data.sets.append(
                SetRecord(
                    source=SOURCE,
                    game=game,
                    language="en",
                    source_set_id=group_id,
                    name=set_name,
                    name_en=set_name,
                    abbreviation=abbreviation,
                    release_date=parse_date(group.get("publishedOn") or group.get("modifiedOn")),
                )
            )

            products_file = game_dir / f"products_{group_id}.json"
            if not products_file.exists():
                continue
            products = json.loads(products_file.read_text(encoding="utf-8"))
            for product in products:
                # Skip sealed product / accessories when we can tell.
                if product.get("isPresale") and not product.get("extendedData"):
                    continue
                ext = extended_map(product)
                number = pick_number(ext, product)
                name = clean_text(product.get("name"))
                if not number or not name:
                    continue
                data.cards.append(
                    CardRecord(
                        source=SOURCE,
                        game=game,
                        language="en",
                        source_set_id=group_id,
                        number=number,
                        name=name,
                        name_en=name,
                        rarity=pick_rarity(ext),
                        card_id=str(product.get("productId") or ""),
                        image_url=clean_text(product.get("imageUrl")),
                    )
                )

    return data if found else None


def game_dir(game: str) -> Path:
    return TCGCSV_RAW / game
