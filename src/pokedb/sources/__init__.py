"""Loaders that turn each raw source into SetRecord / CardRecord objects.

Sources are listed in merge precedence order: earlier sources win when two
sources disagree about a field.
"""

from __future__ import annotations

from ..records import SourceData
from . import database_xlsx, pikaqian_xlsx, tcgdex

# Order matters. database.xlsx is a hand-curated set list and is treated as the
# spine; pikaqian is the authoritative Simplified Chinese card source; TCGdex
# supplies every language's card lists.
LOADERS = (
    database_xlsx.load,
    pikaqian_xlsx.load,
    tcgdex.load,
)


def load_all() -> list[SourceData]:
    return [data for data in (loader() for loader in LOADERS) if data is not None]
