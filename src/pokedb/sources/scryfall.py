"""Load Scryfall bulk All-Cards dump for Magic: The Gathering (all languages).

Expects ``data/raw/scryfall/all_cards.jsonl`` (or ``.jsonl.gz``) written by
``fetch_scryfall``.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from ..config import SCRYFALL_RAW
from ..normalize import clean_text, parse_date
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "scryfall"
GAME = "mtg"

# Scryfall language codes we keep; others are skipped.
_LANG_MAP = {
    "en": "en",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "it": "it",
    "pt": "pt",
    "ja": "ja",
    "ko": "ko",
    "ru": "ru",
    "zhs": "zhs",
    "zht": "zht",
    "he": "he",
    "la": "la",
    "grc": "grc",
    "ar": "ar",
    "sa": "sa",
    "ph": "ph",
    "qya": "qya",
    "dw": "dw",
}


def _open_cards() -> Path | None:
    for name in ("all_cards.jsonl", "all_cards.jsonl.gz", "default_cards.jsonl"):
        path = SCRYFALL_RAW / name
        if path.exists():
            return path
    return None


def _iter_lines(path: Path):
    if path.suffix == ".gz" or path.name.endswith(".jsonl.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                yield line
    else:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                yield line


def load() -> SourceData | None:
    path = _open_cards()
    if path is None:
        return None

    data = SourceData(name=SOURCE)
    seen_sets: set[tuple[str, str]] = set()

    for line in _iter_lines(path):
        line = line.strip()
        if not line:
            continue
        card = json.loads(line)
        lang = _LANG_MAP.get(card.get("lang") or "")
        if not lang:
            continue
        set_code = clean_text(card.get("set"))
        number = clean_text(card.get("collector_number"))
        if not set_code or not number:
            continue

        set_key = (lang, set_code.lower())
        if set_key not in seen_sets:
            seen_sets.add(set_key)
            data.sets.append(
                SetRecord(
                    source=SOURCE,
                    game=GAME,
                    language=lang,
                    source_set_id=set_code.lower(),
                    name=clean_text(card.get("set_name")),
                    name_en=clean_text(card.get("set_name")),
                    abbreviation=set_code.upper(),
                    release_date=parse_date(card.get("released_at")),
                )
            )

        printed = clean_text(card.get("printed_name"))
        name = printed or clean_text(card.get("name")) or ""
        if not name:
            continue
        faces = card.get("image_uris") or {}
        if not faces and card.get("card_faces"):
            faces = (card["card_faces"][0] or {}).get("image_uris") or {}

        data.cards.append(
            CardRecord(
                source=SOURCE,
                game=GAME,
                language=lang,
                source_set_id=set_code.lower(),
                number=number,
                name=name,
                name_en=clean_text(card.get("name")),
                rarity=clean_text(card.get("rarity")),
                card_type=clean_text(card.get("type_line") or card.get("printed_type_line")),
                card_id=clean_text(card.get("id")),
                image_url=clean_text(faces.get("normal") or faces.get("large")),
            )
        )

    return data if data.sets else None
