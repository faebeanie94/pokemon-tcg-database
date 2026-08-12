"""Load ``pikaqian_cards.xlsx``: Simplified Chinese sets and cards.

TCGdex only carries a fraction of the Simplified Chinese cards, so this file is
the authoritative source for that language. It supplies both the Chinese name
and an English name for every set and card.
"""

from __future__ import annotations

from ..normalize import clean_text, parse_date
from ..records import CardRecord, SetRecord, SourceData
from ._excel import cell, find_source_file, match_columns, read_sheets

SOURCE = "pikaqian_cards.xlsx"
LANGUAGE = "zh-cn"

SET_SYNONYMS = {
    "source_set_id": ("id", "set id", "set_id"),
    "name_en": ("name", "english name"),
    "name": ("local_name", "local name", "chinese name"),
    "series_name": ("series", "era"),
    "release_date": ("release_date", "release date", "released"),
    "card_count": ("card_count.actual", "card count", "card_count"),
    "logo_url": ("pack_image_url", "pack image", "image"),
}

CARD_SYNONYMS = {
    "source_set_id": ("card_set_id", "set id", "set_id"),
    "number": ("card_number", "number", "no."),
    "name_en": ("name", "english name"),
    "name": ("local_name", "local name", "chinese name"),
    "rarity": ("rarity_label", "rarity"),
    "card_type": ("card_type", "type"),
    "card_id": ("id",),
    "image_url": ("image_url", "image"),
}


def load() -> SourceData | None:
    path = find_source_file(SOURCE)
    if path is None:
        return None

    data = SourceData(name=SOURCE)

    for sheet_name, frame in read_sheets(path):
        if frame.empty:
            continue
        headers = [str(column) for column in frame.columns]
        lowered = {header.lower() for header in headers}
        is_cards = "card_number" in lowered or "card_set_id" in lowered

        if is_cards:
            mapping = match_columns(headers, CARD_SYNONYMS)
            for _, record in frame.iterrows():
                set_id = clean_text(cell(record, mapping, "source_set_id"))
                number = clean_text(cell(record, mapping, "number"))
                name = clean_text(cell(record, mapping, "name"))
                name_en = clean_text(cell(record, mapping, "name_en"))
                if not set_id or not number or not (name or name_en):
                    continue
                data.cards.append(
                    CardRecord(
                        source=SOURCE,
                        language=LANGUAGE,
                        source_set_id=set_id,
                        number=number,
                        name=name or name_en,
                        name_en=name_en,
                        rarity=clean_text(cell(record, mapping, "rarity")),
                        card_type=clean_text(cell(record, mapping, "card_type")),
                        card_id=clean_text(cell(record, mapping, "card_id")),
                        image_url=clean_text(cell(record, mapping, "image_url")),
                    )
                )
        else:
            mapping = match_columns(headers, SET_SYNONYMS)
            if "source_set_id" not in mapping:
                continue
            for _, record in frame.iterrows():
                set_id = clean_text(cell(record, mapping, "source_set_id"))
                if not set_id:
                    continue
                count = clean_text(cell(record, mapping, "card_count"))
                data.sets.append(
                    SetRecord(
                        source=SOURCE,
                        language=LANGUAGE,
                        source_set_id=set_id,
                        name=clean_text(cell(record, mapping, "name")),
                        name_en=clean_text(cell(record, mapping, "name_en")),
                        abbreviation=set_id,
                        release_date=parse_date(cell(record, mapping, "release_date")),
                        series_name=clean_text(cell(record, mapping, "series_name")),
                        card_count_official=int(float(count)) if _is_number(count) else None,
                        logo_url=clean_text(cell(record, mapping, "logo_url")),
                    )
                )

    return data if (data.sets or data.cards) else None


def _is_number(value: str | None) -> bool:
    if not value:
        return False
    try:
        float(value)
    except ValueError:
        return False
    return True
