"""Load ``build/composed_catalog.sqlite`` into the live grading database.

Produced by ``scripts/compose_xlsx_catalog.py`` from the dump workbooks
(Scryfall / TCGdex / YGO / apitcg / CardTrader / …). Registered **last** in
``LOADERS`` so dedicated raw dumps still win on conflicts; this source fills
gaps and adds games that have no other loader (Digimon, Vanguard, …).
"""

from __future__ import annotations

import sqlite3

from ..config import BUILD, LANGUAGE_CODES
from ..normalize import clean_text, normalize_code, normalize_name, slugify
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "composed_xlsx"
COMPOSED_DB = BUILD / "composed_catalog.sqlite"

# Dump aliases → catalog language codes present in ``languages``.
_LANG_MAP = {
    "chn": "zh-cn",
    "jp": "ja",
    "jpn": "ja",
    "jap": "ja",
    "kr": "ko",
    "eng": "en",
}


def load() -> SourceData | None:
    if not COMPOSED_DB.exists():
        return None

    connection = sqlite3.connect(f"file:{COMPOSED_DB}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT game, language, set_name, set_code, number, name, name_en,
                   rarity, card_type, variant, image_url, source
              FROM cards
             ORDER BY game, language, set_code, set_name, number, name
            """
        ).fetchall()
    finally:
        connection.close()

    if not rows:
        return None

    data = SourceData(name=SOURCE)
    seen_sets: set[tuple[str, str, str]] = set()

    for row in rows:
        game = clean_text(row["game"])
        name = clean_text(row["name"])
        if not game or not name:
            continue

        language = _language(row["language"])
        set_code = clean_text(row["set_code"])
        set_name = clean_text(row["set_name"])
        set_id = (
            normalize_code(set_code)
            or normalize_name(set_name)
            or slugify(set_name or set_code or "set")
        )
        number = clean_text(row["number"]) or slugify(name)[:48]
        parallel = clean_text(row["variant"])

        set_key = (game, language, set_id)
        if set_key not in seen_sets:
            seen_sets.add(set_key)
            data.sets.append(
                SetRecord(
                    source=SOURCE,
                    game=game,
                    language=language,
                    source_set_id=set_id,
                    name=set_name or set_code or set_id,
                    name_en=set_name if language == "en" else None,
                    abbreviation=set_code.upper() if set_code else None,
                )
            )

        data.cards.append(
            CardRecord(
                source=SOURCE,
                game=game,
                language=language,
                source_set_id=set_id,
                number=number,
                name=name,
                name_en=clean_text(row["name_en"]) or (name if language == "en" else None),
                rarity=clean_text(row["rarity"]),
                card_type=clean_text(row["card_type"]),
                image_url=clean_text(row["image_url"]),
                parallel=parallel,
                display_name=name,
            )
        )

    return data if data.sets or data.cards else None


def _language(value: object) -> str:
    text = (clean_text(value) or "en").lower()
    text = _LANG_MAP.get(text, text)
    if text in LANGUAGE_CODES:
        return text
    return "und"
