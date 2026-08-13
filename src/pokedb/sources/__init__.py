"""Loaders that turn each raw source into SetRecord / CardRecord objects.

Sources are listed in merge precedence order: earlier sources win when two
sources disagree about a field. Pokémon sources come first so the existing
spine (database.xlsx) still wins within that game; other games are appended.

Language-rich dumps (Scryfall, YGOPRODeck, Lorcast, GoAgain, apitcg) are
registered before TCGCSV so multilingual / richer data wins when both are
present for the same game.
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

# Flat discovery order (what ``load_all`` runs). Earlier sources win on
# field-level conflicts when a single global merge order is used.
LOADERS = (
    database_xlsx.load,
    pikaqian_xlsx.load,
    tcgdex.load,
    sports_database_xlsx.load,
    sports_json.load,
    sports_xlsx.load,
    tcdb.load,
    beckett.load,
    # Language-rich sources before TCGCSV (Phase 4).
    scryfall.load,
    ygoprodeck.load,
    lorcast.load,
    goagain.load,
    apitcg.load,
    tcgcsv.load,
)


def load_all() -> list[SourceData]:
    return [data for data in (loader() for loader in LOADERS) if data is not None]
