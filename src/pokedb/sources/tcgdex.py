"""Load the raw TCGdex API dumps written by ``python -m pokedb fetch``."""

from __future__ import annotations

import json

from ..config import LANGUAGES, TCGDEX_RAW
from ..normalize import clean_text, parse_date
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "tcgdex"


def _abbreviation(payload: dict) -> str | None:
    raw = payload.get("abbreviation") or {}
    # Japanese-stream sets carry no separate code: the identifier printed on the
    # card (SV1S, S12a, ...) is the abbreviation collectors use.
    return clean_text(raw.get("official")) or clean_text(raw.get("localized")) or payload["id"]


def load() -> SourceData | None:
    data = SourceData(name=SOURCE)
    found = False

    for language in (item["code"] for item in LANGUAGES):
        raw_file = TCGDEX_RAW / f"{language}.json"
        if not raw_file.exists():
            continue
        found = True
        payload = json.loads(raw_file.read_text(encoding="utf-8"))

        for set_payload in payload["sets"].values():
            set_id = set_payload["id"]
            counts = set_payload.get("cardCount") or {}
            serie = set_payload.get("serie") or {}
            data.sets.append(
                SetRecord(
                    source=SOURCE,
                    language=language,
                    source_set_id=set_id,
                    name=clean_text(set_payload.get("name")),
                    abbreviation=_abbreviation(set_payload),
                    release_date=parse_date(set_payload.get("releaseDate")),
                    series_name=clean_text(serie.get("name")),
                    card_count_official=counts.get("official"),
                    card_count_total=counts.get("total"),
                    logo_url=set_payload.get("logo"),
                    symbol_url=set_payload.get("symbol"),
                )
            )

            for card in set_payload.get("cards") or []:
                number = clean_text(card.get("localId"))
                name = clean_text(card.get("name"))
                if not number or not name:
                    continue
                data.cards.append(
                    CardRecord(
                        source=SOURCE,
                        language=language,
                        source_set_id=set_id,
                        number=number,
                        name=name,
                        card_id=clean_text(card.get("id")),
                        image_url=clean_text(card.get("image")),
                    )
                )

    return data if found else None
