"""One Piece–focused apitcg loader alias.

Plan name: ``sources/apitcg_onepiece.py``. The shared ``apitcg`` loader already
covers One Piece and DBS Fusion World; Japanese Bandai cardlist scrape remains
deferred — see docs/DATA_SOURCES.md.
"""

from .apitcg import SOURCE, load

GAME = "onepiece"

__all__ = ["GAME", "SOURCE", "load"]
