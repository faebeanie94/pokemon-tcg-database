"""Load Bandai Japanese One Piece cardlist dumps.

Complement to TCGCSV English One Piece data. Expects
``data/raw/bandai/onepiece/sets.json`` and ``cards.json`` produced by
``fetch_bandai_onepiece`` (or a manual scrape of the official JP cardlist).
"""

from __future__ import annotations

import json

from ..config import DATA_RAW
from ..normalize import clean_text
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "bandai_onepiece"
GAME = "onepiece"
RAW = DATA_RAW / "bandai" / "onepiece"


def load() -> SourceData | None:
    sets_file = RAW / "sets.json"
    cards_file = RAW / "cards.json"
    if not sets_file.exists() and not cards_file.exists():
        return None

    data = SourceData(name=SOURCE)
    seen: set[str] = set()

    if sets_file.exists():
        sets = json.loads(sets_file.read_text(encoding="utf-8"))
        if isinstance(sets, dict):
            sets = sets.get("data") or sets.get("sets") or []
        for set_payload in sets:
            set_id = clean_text(set_payload.get("id") or set_payload.get("code"))
            name = clean_text(set_payload.get("name"))
            if not set_id:
                continue
            seen.add(set_id.lower())
            data.sets.append(
                SetRecord(
                    source=SOURCE,
                    game=GAME,
                    language="ja",
                    source_set_id=set_id.lower(),
                    name=name,
                    name_en=clean_text(set_payload.get("name_en")),
                    abbreviation=set_id.upper(),
                )
            )

    if cards_file.exists():
        cards = json.loads(cards_file.read_text(encoding="utf-8"))
        if isinstance(cards, dict):
            cards = cards.get("data") or cards.get("cards") or []
        for card in cards:
            set_id = clean_text(card.get("set") or card.get("set_id") or card.get("setCode"))
            number = clean_text(str(card.get("number") or card.get("id") or ""))
            name = clean_text(card.get("name") or card.get("name_ja"))
            if not set_id or not number or not name:
                continue
            sid = set_id.lower()
            if sid not in seen:
                seen.add(sid)
                data.sets.append(
                    SetRecord(
                        source=SOURCE,
                        game=GAME,
                        language="ja",
                        source_set_id=sid,
                        name=set_id,
                        abbreviation=set_id.upper(),
                    )
                )
            data.cards.append(
                CardRecord(
                    source=SOURCE,
                    game=GAME,
                    language="ja",
                    source_set_id=sid,
                    number=number,
                    name=name,
                    name_en=clean_text(card.get("name_en")),
                    rarity=clean_text(card.get("rarity")),
                    card_type=clean_text(card.get("type") or card.get("category")),
                    card_id=clean_text(card.get("id")),
                    image_url=clean_text(card.get("image_url") or card.get("image")),
                )
            )

    return data if data.sets or data.cards else None
