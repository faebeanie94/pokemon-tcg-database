"""Load apitcg.com dumps (One Piece, DBS Fusion World, and related Bandai games)."""

from __future__ import annotations

import json

from ..config import APITCG_RAW
from ..normalize import clean_text
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "apitcg"

# slug on disk / API -> our game code
SLUGS = {
    "one-piece": "onepiece",
    "dragon-ball-fusion": "dbsfw",
    "dragon-ball-super-fusion-world": "dbsfw",
}


def load() -> SourceData | None:
    if not APITCG_RAW.exists():
        return None

    data = SourceData(name=SOURCE)
    found = False

    for slug, game in SLUGS.items():
        sets_file = APITCG_RAW / slug / "sets.json"
        cards_file = APITCG_RAW / slug / "cards.json"
        if not sets_file.exists() and not cards_file.exists():
            continue
        found = True
        seen: set[str] = set()

        if sets_file.exists():
            sets = json.loads(sets_file.read_text(encoding="utf-8"))
            if isinstance(sets, dict):
                sets = sets.get("data") or sets.get("results") or []
            for set_payload in sets:
                set_id = clean_text(set_payload.get("id") or set_payload.get("code"))
                if not set_id:
                    continue
                seen.add(set_id.lower())
                data.sets.append(
                    SetRecord(
                        source=SOURCE,
                        game=game,
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
                set_id = clean_text(card.get("set") or card.get("set_id") or card.get("code"))
                number = clean_text(str(card.get("number") or card.get("id") or ""))
                name = clean_text(card.get("name"))
                if not set_id or not number or not name:
                    continue
                sid = set_id.lower()
                if sid not in seen:
                    seen.add(sid)
                    data.sets.append(
                        SetRecord(
                            source=SOURCE,
                            game=game,
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
                        game=game,
                        language="en",
                        source_set_id=sid,
                        number=number,
                        name=name,
                        name_en=name,
                        rarity=clean_text(card.get("rarity")),
                        card_type=clean_text(card.get("type") or card.get("color")),
                        card_id=clean_text(str(card.get("id") or "")),
                        image_url=clean_text(card.get("images") if isinstance(card.get("images"), str) else None)
                        or clean_text((card.get("images") or {}).get("large") if isinstance(card.get("images"), dict) else None)
                        or clean_text(card.get("image_url") or card.get("image")),
                    )
                )

    return data if found else None
