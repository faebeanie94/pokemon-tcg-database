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
    beckett,
    database_xlsx,
    goagain,
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
    lorcast.load,
    goagain.load,
    apitcg.load,
    tcgcsv.load,
)

# Preferred merge order per game (earlier wins). Sources absent from a build
# are skipped. Games not listed fall back to the loaded flat order.
SOURCE_ORDER_BY_GAME: dict[str, list[str]] = {
    "pokemon": ["database.xlsx", "pikaqian_cards.xlsx", "tcgdex"],
    "sports": [
        "sports_database.xlsx",
        "sports_seed",
        "sports_checklists.xlsx",
        "tcdb",
        "beckett",
    ],
    "mtg": ["scryfall", "tcgcsv"],
    "yugioh": ["ygoprodeck", "tcgcsv"],
    "lorcana": ["lorcast", "tcgcsv"],
    "fleshblood": ["goagain", "tcgcsv"],
    "onepiece": ["apitcg", "tcgcsv"],
    "dbsfw": ["apitcg", "tcgcsv"],
    "weiss": ["tcgcsv"],
    "dbz": ["tcgcsv"],
    "dbs": ["tcgcsv"],
    "metazoo": ["tcgcsv"],
    "warhammer": ["tcgcsv"],
    "dicemasters": ["tcgcsv"],
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
