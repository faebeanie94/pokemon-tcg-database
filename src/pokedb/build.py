"""Build the SQLite database by merging every source."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from .config import BUILD, DB_PATH, LANGUAGES
from .match import SetRegistry, merge_cards
from .normalize import release_year
from .records import SourceData
from .sources import load_all

SCHEMA = Path(__file__).with_name("schema.sql")


def _insert(connection: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    columns = list(rows[0])
    placeholders = ", ".join(f":{column}" for column in columns)
    connection.executemany(
        f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows
    )
    return len(rows)


def _set_row(canonical, source_order: list[str]) -> dict[str, Any]:
    pick = lambda attribute: canonical.first(source_order, attribute)  # noqa: E731
    release_date = pick("release_date")
    tcgdex_record = canonical.records.get("tcgdex")
    pikaqian_record = canonical.records.get("pikaqian_cards.xlsx")
    contributing = [record.source for record in canonical.ordered(source_order)]
    return {
        "set_uid": canonical.set_uid,
        "language": canonical.language,
        "name": pick("name") or pick("name_en"),
        "name_en": pick("name_en"),
        "abbreviation": pick("abbreviation"),
        "release_date": release_date,
        "release_year": release_year(release_date),
        "series_name": pick("series_name"),
        "sequence": pick("sequence"),
        "card_count_official": pick("card_count_official"),
        "card_count_total": pick("card_count_total"),
        "card_count_loaded": 0,
        "tcgdex_set_id": tcgdex_record.source_set_id if tcgdex_record else None,
        "pikaqian_set_id": pikaqian_record.source_set_id if pikaqian_record else None,
        "logo_url": pick("logo_url"),
        "symbol_url": pick("symbol_url"),
        "sources": ",".join(contributing),
        "source_count": len(contributing),
    }


def _derive_english_names(card_rows: list[dict[str, Any]]) -> int:
    """Fill in English card names for languages that only ship a local name."""
    from .translate import load_translator

    translator = load_translator()
    if translator is None:
        return 0

    derived = 0
    for row in card_rows:
        if row.get("name_en") or not translator.supports(row["language"]):
            continue
        english = translator.english_name(row["language"], row["name"])
        if english:
            row["name_en"] = english
            row["name_en_source"] = "pokeapi"
            derived += 1
    return derived


def build(db_path: Path = DB_PATH) -> dict[str, Any]:
    sources: list[SourceData] = load_all()
    if not sources:
        raise SystemExit(
            "No sources found. Run `python -m pokedb fetch` and/or add the spreadsheets."
        )

    source_order = [data.name for data in sources]
    registry = SetRegistry(source_order)
    for data in sources:
        for record in data.sets:
            registry.add(record)
    date_links = registry.link_by_unique_release_date()
    registry.assign_uids()

    all_cards = [card for data in sources for card in data.cards]
    card_rows, orphans = merge_cards(all_cards, registry, source_order)
    derived_names = _derive_english_names(card_rows)

    BUILD.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(SCHEMA.read_text(encoding="utf-8"))
    connection.execute("PRAGMA foreign_keys = ON")

    _insert(connection, "languages", [dict(language) for language in LANGUAGES])
    _insert(
        connection,
        "sets",
        [_set_row(canonical, source_order) for canonical in registry.canonical],
    )
    _insert(
        connection,
        "set_sources",
        [
            {
                "set_uid": canonical.set_uid,
                "source": record.source,
                "source_set_id": record.source_set_id,
                "name": record.name,
                "name_en": record.name_en,
                "abbreviation": record.abbreviation,
                "release_date": record.release_date,
                "series_name": record.series_name,
                "sequence": record.sequence,
                "matched_by": canonical.matched_by.get(record.source),
            }
            for canonical in registry.canonical
            for record in canonical.records.values()
        ],
    )
    _insert(connection, "cards", card_rows)

    connection.execute(
        """
        UPDATE sets
           SET card_count_loaded = (
                   SELECT COUNT(*) FROM cards WHERE cards.set_uid = sets.set_uid
               )
        """
    )
    connection.commit()

    stats = {
        "sources": len(sources),
        "sets": connection.execute("SELECT COUNT(*) FROM sets").fetchone()[0],
        "cards": connection.execute("SELECT COUNT(*) FROM cards").fetchone()[0],
        "languages": connection.execute(
            "SELECT COUNT(DISTINCT language) FROM sets"
        ).fetchone()[0],
        "sets_multi_source": connection.execute(
            "SELECT COUNT(*) FROM sets WHERE source_count > 1"
        ).fetchone()[0],
        "linked_by_release_date": date_links,
        "english_names_derived": derived_names,
        "orphan_cards": len(orphans),
    }

    _insert(
        connection,
        "build_info",
        [
            {"key": "built_at", "value": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            {"key": "source_order", "value": ",".join(source_order)},
            *[{"key": f"count_{name}", "value": str(value)} for name, value in stats.items()],
        ],
    )
    connection.commit()
    connection.execute("VACUUM")
    connection.close()

    for note in registry.notes[:10]:
        print(f"  note: {note}")
    if orphans:
        print(f"  ! {len(orphans)} card rows referenced an unknown set and were skipped")
    return stats
