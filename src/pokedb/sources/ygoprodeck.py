"""Load YGOPRODeck dumps for Yu-Gi-Oh! (en/fr/de/it/pt)."""

from __future__ import annotations

import json

from ..config import YGOPRODECK_RAW
from ..normalize import clean_text
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "ygoprodeck"
GAME = "yugioh"
LANGUAGES = ("en", "fr", "de", "it", "pt")


def load() -> SourceData | None:
    if not YGOPRODECK_RAW.exists():
        return None

    data = SourceData(name=SOURCE)
    found = False
    seen_sets: set[tuple[str, str]] = set()

    for language in LANGUAGES:
        path = YGOPRODECK_RAW / f"{language}.json"
        if not path.exists():
            continue
        found = True
        payload = json.loads(path.read_text(encoding="utf-8"))
        cards = payload.get("data", payload) if isinstance(payload, dict) else payload
        for card in cards:
            name = clean_text(card.get("name"))
            if not name:
                continue
            for printing in card.get("card_sets") or []:
                set_name = clean_text(printing.get("set_name"))
                set_code = clean_text(printing.get("set_code"))
                number = clean_text(printing.get("set_code"))
                # YGO set_code on a printing is often "LOB-EN001" — use the full
                # code as the card number; set id is the set name slug.
                if not set_name:
                    continue
                set_id = set_code.split("-")[0].lower() if set_code and "-" in set_code else (
                    set_name.lower().replace(" ", "-")
                )
                card_number = set_code or number or "0"
                key = (language, set_id)
                if key not in seen_sets:
                    seen_sets.add(key)
                    data.sets.append(
                        SetRecord(
                            source=SOURCE,
                            game=GAME,
                            language=language,
                            source_set_id=set_id,
                            name=set_name,
                            name_en=set_name if language == "en" else None,
                            abbreviation=set_id.upper(),
                        )
                    )
                data.cards.append(
                    CardRecord(
                        source=SOURCE,
                        game=GAME,
                        language=language,
                        source_set_id=set_id,
                        number=card_number,
                        name=name,
                        name_en=name if language == "en" else None,
                        rarity=clean_text(printing.get("set_rarity")),
                        card_type=clean_text(card.get("type")),
                        card_id=str(card.get("id") or ""),
                        image_url=_image(card),
                    )
                )

    return data if found else None


def _image(card: dict) -> str | None:
    images = card.get("card_images") or []
    if not images:
        return None
    return clean_text(images[0].get("image_url"))
