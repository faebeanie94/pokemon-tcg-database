"""Loaders that turn each raw source into SetRecord / CardRecord objects.

Sources are listed in merge precedence order: earlier sources win when two
sources disagree about a field. Pokémon sources come first so the existing
spine (database.xlsx) still wins within that game; other games are appended.
"""

from __future__ import annotations

from ..records import SourceData
from . import (
    apitcg,
    bandai_onepiece,
    database_xlsx,
    goagain,
    lorcast,
    pikaqian_xlsx,
    scryfall,
    sports_json,
    sports_xlsx,
    tcgcsv,
    tcgdex,
    ygoprodeck,
)

# Order matters within a game. database.xlsx is the Pokémon spine; pikaqian is
# the authoritative Simplified Chinese card source; TCGdex supplies every
# language's card lists. Sports and other-game loaders follow.
LOADERS = (
    database_xlsx.load,
    pikaqian_xlsx.load,
    tcgdex.load,
    sports_json.load,
    sports_xlsx.load,
    tcgcsv.load,
    scryfall.load,
    ygoprodeck.load,
    lorcast.load,
    goagain.load,
    apitcg.load,
    bandai_onepiece.load,
)


def load_all() -> list[SourceData]:
    return [data for data in (loader() for loader in LOADERS) if data is not None]
