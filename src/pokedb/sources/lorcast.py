"""Load Lorcast dumps for Disney Lorcana."""

from __future__ import annotations

import json

from ..config import LORCAST_RAW
from ..normalize import clean_text, parse_date
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "lorcast"
GAME = "lorcana"


def load() -> SourceData | None:
    sets_file = LORCAST_RAW / "sets.json"
    if not sets_file.exists():
        return None

    data = SourceData(name=SOURCE)
    sets = json.loads(sets_file.read_text(encoding="utf-8"))
    if isinstance(sets, dict):
        sets = sets.get("results") or sets.get("data") or []

    for set_payload in sets:
        set_code = clean_text(set_payload.get("code") or set_payload.get("id"))
        set_name = clean_text(set_payload.get("name"))
        if not set_code:
            continue
        data.sets.append(
            SetRecord(
                source=SOURCE,
                game=GAME,
                language="en",
                source_set_id=set_code,
                name=set_name,
                name_en=set_name,
                abbreviation=set_code,
                release_date=parse_date(set_payload.get("released_at")),
            )
        )
        cards_file = LORCAST_RAW / f"cards_{set_code}.json"
        if not cards_file.exists():
            continue
        cards = json.loads(cards_file.read_text(encoding="utf-8"))
        if isinstance(cards, dict):
            cards = cards.get("results") or cards.get("data") or cards.get("cards") or []
        for card in cards:
            number = clean_text(str(card.get("collector_number") or card.get("number") or ""))
            name = clean_text(card.get("name"))
            if not number or not name:
                continue
            images = card.get("image_uris") or {}
            digital = images.get("digital") if isinstance(images, dict) else {}
            data.cards.append(
                CardRecord(
                    source=SOURCE,
                    game=GAME,
                    language="en",
                    source_set_id=set_code,
                    number=number,
                    name=name,
                    name_en=name,
                    rarity=clean_text(card.get("rarity")),
                    card_type=clean_text(card.get("type")),
                    card_id=clean_text(card.get("id")),
                    image_url=clean_text(
                        (digital or {}).get("large")
                        or (digital or {}).get("normal")
                        or images.get("large")
                    ),
                )
            )

    return data if data.sets else None
