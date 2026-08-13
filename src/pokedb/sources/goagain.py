"""Load GoAgain / Flesh and Blood dumps."""

from __future__ import annotations

import json

from ..config import GOAGAIN_RAW
from ..normalize import clean_text
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "goagain"
GAME = "fleshblood"


def load() -> SourceData | None:
    sets_file = GOAGAIN_RAW / "sets.json"
    cards_file = GOAGAIN_RAW / "cards.json"
    if not sets_file.exists() and not cards_file.exists():
        return None

    data = SourceData(name=SOURCE)
    seen_sets: set[str] = set()

    if sets_file.exists():
        sets = json.loads(sets_file.read_text(encoding="utf-8"))
        if isinstance(sets, dict):
            sets = sets.get("data") or sets.get("results") or []
        for set_payload in sets:
            set_id = clean_text(set_payload.get("id") or set_payload.get("code"))
            if not set_id:
                continue
            seen_sets.add(set_id.lower())
            data.sets.append(
                SetRecord(
                    source=SOURCE,
                    game=GAME,
                    language="en",
                    source_set_id=set_id.lower(),
                    name=clean_text(set_payload.get("name")),
                    name_en=clean_text(set_payload.get("name")),
                    abbreviation=set_id.upper(),
                )
            )

    if cards_file.exists():
        cards = json.loads(cards_file.read_text(encoding="utf-8"))
        if isinstance(cards, dict):
            cards = cards.get("data") or cards.get("results") or []
        for card in cards:
            set_id = clean_text(
                card.get("set")
                or card.get("set_id")
                or (card.get("set_info") or {}).get("id")
            )
            number = clean_text(str(card.get("number") or card.get("collector_number") or ""))
            name = clean_text(card.get("name"))
            if not set_id or not number or not name:
                continue
            sid = set_id.lower()
            if sid not in seen_sets:
                seen_sets.add(sid)
                data.sets.append(
                    SetRecord(
                        source=SOURCE,
                        game=GAME,
                        language="en",
                        source_set_id=sid,
                        name=set_id,
                        name_en=set_id,
                        abbreviation=set_id.upper(),
                    )
                )
            data.cards.append(
                CardRecord(
                    source=SOURCE,
                    game=GAME,
                    language="en",
                    source_set_id=sid,
                    number=number,
                    name=name,
                    name_en=name,
                    rarity=clean_text(card.get("rarity")),
                    card_type=clean_text(card.get("type")),
                    card_id=clean_text(card.get("id")),
                    image_url=clean_text(card.get("image_url") or card.get("image")),
                )
            )

    return data if data.sets or data.cards else None
