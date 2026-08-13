"""Load staged Bandai JP One Piece dumps from ``data/raw/bandai_onepiece/``.

See ``fetch_bandai_onepiece`` for the dump shape. English rows stay with
TCGCSV / apitcg; this loader only emits ``language=ja`` (or whatever the dump
declares) under ``game=onepiece``.
"""

from __future__ import annotations

import json

from ..config import DATA_RAW
from ..normalize import clean_text, parse_date
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "bandai_onepiece"
GAME = "onepiece"
RAW = DATA_RAW / "bandai_onepiece"


def load() -> SourceData | None:
    sets_path = RAW / "sets.json"
    cards_path = RAW / "cards.json"
    combined = RAW / "dump.json"
    if not sets_path.exists() and not cards_path.exists() and not combined.exists():
        return None

    if combined.exists() and not (sets_path.exists() or cards_path.exists()):
        payload = json.loads(combined.read_text(encoding="utf-8"))
        sets = payload.get("sets") or []
        cards = payload.get("cards") or []
    else:
        sets = json.loads(sets_path.read_text(encoding="utf-8")) if sets_path.exists() else []
        cards = json.loads(cards_path.read_text(encoding="utf-8")) if cards_path.exists() else []

    data = SourceData(name=SOURCE)
    for set_payload in sets:
        if not isinstance(set_payload, dict):
            continue
        set_id = clean_text(set_payload.get("id") or set_payload.get("abbreviation"))
        name = clean_text(set_payload.get("name"))
        if not set_id or not name:
            continue
        data.sets.append(
            SetRecord(
                source=SOURCE,
                game=GAME,
                language=clean_text(set_payload.get("language")) or "ja",
                source_set_id=set_id,
                name=name,
                name_en=clean_text(set_payload.get("name_en")) or name,
                abbreviation=clean_text(set_payload.get("abbreviation")) or set_id,
                release_date=parse_date(set_payload.get("release_date")),
            )
        )

    for card in cards:
        if not isinstance(card, dict):
            continue
        set_id = clean_text(card.get("set_id"))
        number = clean_text(str(card.get("number") or ""))
        name = clean_text(card.get("name"))
        if not set_id or not number or not name:
            continue
        data.cards.append(
            CardRecord(
                source=SOURCE,
                game=GAME,
                language=clean_text(card.get("language")) or "ja",
                source_set_id=set_id,
                number=number,
                name=name,
                name_en=clean_text(card.get("name_en")),
                rarity=clean_text(card.get("rarity")),
                image_url=clean_text(card.get("image_url")),
            )
        )

    return data if data.sets or data.cards else None
