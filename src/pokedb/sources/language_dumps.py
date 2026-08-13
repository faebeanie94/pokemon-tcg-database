"""Load staged language-gap dumps (Weiss JP, YGO OCG, Lorcana i18n).

See ``fetch_language_dumps``. Each subdirectory under ``data/raw/`` maps to a
game + preferred language; English rows from TCGCSV / dedicated APIs still win
when both exist via ``SOURCE_ORDER_BY_GAME``.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import DATA_RAW
from ..normalize import clean_text, parse_date
from ..records import CardRecord, SetRecord, SourceData


def _load_one(source: str, game: str, directory: Path, default_language: str) -> SourceData | None:
    sets_path = directory / "sets.json"
    cards_path = directory / "cards.json"
    if not sets_path.exists() and not cards_path.exists():
        return None

    sets = json.loads(sets_path.read_text(encoding="utf-8")) if sets_path.exists() else []
    cards = json.loads(cards_path.read_text(encoding="utf-8")) if cards_path.exists() else []
    data = SourceData(name=source)

    for set_payload in sets:
        if not isinstance(set_payload, dict):
            continue
        set_id = clean_text(set_payload.get("id") or set_payload.get("abbreviation"))
        name = clean_text(set_payload.get("name"))
        if not set_id or not name:
            continue
        data.sets.append(
            SetRecord(
                source=source,
                game=game,
                language=clean_text(set_payload.get("language")) or default_language,
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
                source=source,
                game=game,
                language=clean_text(card.get("language")) or default_language,
                source_set_id=set_id,
                number=number,
                name=name,
                name_en=clean_text(card.get("name_en")),
                rarity=clean_text(card.get("rarity")),
                image_url=clean_text(card.get("image_url")),
            )
        )

    return data if data.sets or data.cards else None


def load_weiss_jp() -> SourceData | None:
    return _load_one("weiss_jp", "weiss", DATA_RAW / "weiss_jp", "ja")


def load_ygo_ocg() -> SourceData | None:
    return _load_one("ygo_ocg", "yugioh", DATA_RAW / "ygo_ocg", "ja")


def load_lorcana_i18n() -> SourceData | None:
    return _load_one("lorcana_i18n", "lorcana", DATA_RAW / "lorcana_i18n", "fr")
