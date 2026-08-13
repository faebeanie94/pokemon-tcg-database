"""Loaders that turn each raw source into SetRecord / CardRecord objects.

Sources are listed in merge precedence order: earlier sources win when two
sources disagree about a field. Pokémon sources come first so the existing
spine (database.xlsx) still wins within that game; other games are appended.

Per-game precedence is in ``SOURCE_ORDER_BY_GAME`` — used by ``build`` so
Scryfall beats TCGCSV for Magic, YGOPRODeck beats TCGCSV for Yu-Gi-Oh, etc.
"""

from __future__ import annotations

from ..records import SourceData
from . import (
    apitcg,
    bandai_onepiece,
    beckett,
    composed_catalog,
    database_xlsx,
    goagain,
    language_dumps,
    lorcast,
    pikaqian_xlsx,
    scryfall,
    sports_database_xlsx,
    sports_json,
    sports_xlsx,
    tcdb,
    tcgcsv,
    tcgdex,
    ygoprodeck,
)

# Flat discovery order (what ``load_all`` runs). Field-level wins use
# ``SOURCE_ORDER_BY_GAME`` when a game has multiple sources.
LOADERS = (
    database_xlsx.load,
    pikaqian_xlsx.load,
    tcgdex.load,
    sports_database_xlsx.load,
    sports_json.load,
    sports_xlsx.load,
    tcdb.load,
    beckett.load,
    # Language-rich sources before TCGCSV so they win within their games when
    # both dumps are present (build still applies SOURCE_ORDER_BY_GAME).
    scryfall.load,
    ygoprodeck.load,
    language_dumps.load_ygo_ocg,
    lorcast.load,
    language_dumps.load_lorcana_i18n,
    goagain.load,
    apitcg.load,
    bandai_onepiece.load,
    language_dumps.load_weiss_jp,
    tcgcsv.load,
    # Dump-workbook compose (scripts/compose_xlsx_catalog.py) — last so it
    # fills gaps and adds Digimon / Vanguard / Star Wars / etc.
    composed_catalog.load,
)

# Preferred merge order per game (earlier wins). Sources absent from a build
# are skipped. Games not listed fall back to the loaded flat order.
SOURCE_ORDER_BY_GAME: dict[str, list[str]] = {
    "pokemon": ["database.xlsx", "pikaqian_cards.xlsx", "tcgdex", "composed_xlsx"],
    "sports": [
        "sports_database.xlsx",
        "sports_seed",
        "sports_checklists.xlsx",
        "tcdb",
        "beckett",
        "composed_xlsx",
    ],
    "mtg": ["scryfall", "tcgcsv", "composed_xlsx"],
    "yugioh": ["ygoprodeck", "ygo_ocg", "tcgcsv", "composed_xlsx"],
    "lorcana": ["lorcast", "lorcana_i18n", "tcgcsv", "composed_xlsx"],
    "fleshblood": ["goagain", "tcgcsv", "composed_xlsx"],
    "onepiece": ["bandai_onepiece", "apitcg", "tcgcsv", "composed_xlsx"],
    "dbsfw": ["apitcg", "tcgcsv", "composed_xlsx"],
    "weiss": ["weiss_jp", "tcgcsv", "composed_xlsx"],
    "dbz": ["tcgcsv", "composed_xlsx"],
    "dbs": ["tcgcsv", "composed_xlsx"],
    "metazoo": ["tcgcsv", "composed_xlsx"],
    "warhammer": ["tcgcsv", "composed_xlsx"],
    "dicemasters": ["tcgcsv", "composed_xlsx"],
    "universus": ["tcgcsv", "composed_xlsx"],
    "digimon": ["composed_xlsx"],
    "vanguard": ["composed_xlsx"],
    "starwars": ["composed_xlsx"],
    "sorcery": ["composed_xlsx"],
    "riftbound": ["composed_xlsx"],
    "gundam": ["composed_xlsx"],
    "unionarena": ["composed_xlsx"],
}


def load_all() -> list[SourceData]:
    return [data for data in (loader() for loader in LOADERS) if data is not None]


def source_order_for(game: str, loaded: list[str]) -> list[str]:
    """Return merge precedence for ``game`` given the sources actually loaded."""
    preferred = SOURCE_ORDER_BY_GAME.get(game)
    if not preferred:
        return list(loaded)
    present = set(loaded)
    ordered = [name for name in preferred if name in present]
    ordered.extend(name for name in loaded if name not in ordered)
    return ordered
