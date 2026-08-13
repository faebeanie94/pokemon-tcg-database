"""Help text for sports checklist adapters (TCDB / Beckett).

These sources have no stable public API. Operators normalize dumps with the
scripts under ``apis/``, then ``pokedb build`` loads ``data/raw/tcdb`` and
``data/raw/beckett``.
"""

from __future__ import annotations


def print_tcdb_help() -> None:
    print(
        "  TCDB has no stable public API. Normalize an operator dump with:\n"
        "    python3 apis/tcdb_fetch.py --from-file path/to/dump.json\n"
        "  Output lands in data/raw/tcdb/ and is loaded on the next `pokedb build`."
    )


def print_beckett_help() -> None:
    print(
        "  Beckett has no public checklist API. Normalize an article dump with:\n"
        "    python3 apis/beckett_fetch.py --from-file path/to/article.json\n"
        "  Output lands in data/raw/beckett/ and is loaded on the next `pokedb build`."
    )
