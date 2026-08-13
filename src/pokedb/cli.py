"""Command line entry point: ``python -m pokedb <command>``."""

from __future__ import annotations

import argparse

from .config import DB_PATH, GAME_CODES, LANGUAGE_CODES, TCGCSV_CATEGORIES

FETCH_SOURCES = (
    "tcgdex",
    "tcgcsv",
    "scryfall",
    "ygoprodeck",
    "lorcast",
    "goagain",
    "apitcg",
    "tcdb",
    "beckett",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pokedb",
        description="Build the multi-game trading / sports card database.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="download catalog data from configured sources")
    fetch.add_argument(
        "--source",
        action="append",
        choices=FETCH_SOURCES,
        help="limit to specific sources (repeatable; default: tcgdex only for `update`)",
    )
    fetch.add_argument(
        "--language",
        action="append",
        choices=LANGUAGE_CODES,
        help="limit TCGdex / YGOPRODeck languages (repeatable)",
    )
    fetch.add_argument(
        "--game",
        action="append",
        choices=sorted(set(TCGCSV_CATEGORIES) | set(GAME_CODES)),
        help="limit TCGCSV / apitcg games (repeatable)",
    )

    fetch_tcgcsv = subparsers.add_parser(
        "fetch-tcgcsv", help="download TCGCSV category dumps (alias for fetch --source tcgcsv)"
    )
    fetch_tcgcsv.add_argument(
        "--game",
        action="append",
        choices=sorted(TCGCSV_CATEGORIES),
        help="limit to specific TCGCSV games (repeatable)",
    )
    subparsers.add_parser(
        "fetch-scryfall",
        help="download Scryfall All Cards bulk (alias for fetch --source scryfall)",
    )
    subparsers.add_parser(
        "fetch-sports",
        help="print how to stage TCDB / Beckett sports checklists",
    )

    build_cmd = subparsers.add_parser("build", help="merge every source into the SQLite database")
    build_cmd.add_argument(
        "--game",
        action="append",
        choices=sorted(GAME_CODES),
        help="limit the build to specific games (repeatable)",
    )

    export = subparsers.add_parser("export", help="write the Excel workbook and CSVs")
    export.add_argument("--no-csv", action="store_true", help="only write the Excel workbook")
    subparsers.add_parser("report", help="print coverage and source disagreements")
    subparsers.add_parser("verify", help="check the input spreadsheets against the API data")
    update = subparsers.add_parser(
        "update", help="fetch (tcgdex), build, export and report - the usual refresh"
    )
    update.add_argument("--no-csv", action="store_true", help="only write the Excel workbook")
    update.add_argument(
        "--source",
        action="append",
        choices=FETCH_SOURCES,
        help="extra sources to fetch before build (tcgdex always runs on update)",
    )
    update.add_argument(
        "--game",
        action="append",
        choices=sorted(GAME_CODES),
        help="limit the build to specific games (repeatable)",
    )

    args = parser.parse_args(argv)
    command = args.command

    if command == "fetch-tcgcsv":
        _run_fetch(["tcgcsv"], languages=None, games=getattr(args, "game", None))
        return 0
    if command == "fetch-scryfall":
        _run_fetch(["scryfall"], languages=None, games=None)
        return 0
    if command == "fetch-sports":
        from .fetch_sports import print_beckett_help, print_tcdb_help

        print("Staging sports checklists (TCDB + Beckett)...")
        print_tcdb_help()
        print_beckett_help()
        return 0

    if command in {"fetch", "update"}:
        sources = list(getattr(args, "source", None) or [])
        if command == "update" and "tcgdex" not in sources:
            sources = ["tcgdex", *sources]
        if command == "fetch" and not sources:
            sources = ["tcgdex"]
        _run_fetch(
            sources,
            languages=getattr(args, "language", None),
            games=getattr(args, "game", None),
        )

    if command in {"build", "update"}:
        from .build import build

        print("Building database...")
        stats = build(games=getattr(args, "game", None))
        print(f"  {DB_PATH}: " + ", ".join(f"{key}={value}" for key, value in stats.items()))

    if command in {"export", "update"}:
        from .export import export_all

        print("Writing exports...")
        for path in export_all(write_csv=not getattr(args, "no_csv", False)):
            print(f"  {path}")

    if command == "verify":
        from .verify import verify

        return 0 if verify() else 1

    if command in {"report", "update"}:
        from .report import print_report

        print_report()

    return 0


def _run_fetch(
    sources: list[str],
    *,
    languages: list[str] | None,
    games: list[str] | None,
) -> None:
    for source in sources:
        if source == "tcgdex":
            from .fetch_tcgdex import fetch_all

            print("Fetching TCGdex data...")
            fetch_all(languages)
        elif source == "tcgcsv":
            from .fetch_tcgcsv import fetch_all

            print("Fetching TCGCSV data...")
            fetch_all(games)
        elif source == "scryfall":
            from .fetch_scryfall import fetch_all

            print("Fetching Scryfall bulk data...")
            print(f"  wrote {fetch_all()}")
        elif source == "ygoprodeck":
            from .fetch_ygoprodeck import fetch_all

            print("Fetching YGOPRODeck data...")
            fetch_all(languages)
        elif source == "lorcast":
            from .fetch_lorcast import fetch_all

            print("Fetching Lorcast data...")
            print(f"  {fetch_all()} cards")
        elif source == "goagain":
            from .fetch_goagain import fetch_all

            print("Fetching GoAgain (Flesh and Blood) data...")
            print(f"  {fetch_all()}")
        elif source == "apitcg":
            from .fetch_apitcg import fetch_all

            print("Fetching apitcg data...")
            print(f"  {fetch_all(games)}")
        elif source == "tcdb":
            from .fetch_sports import print_tcdb_help

            print("Staging TCDB sports checklists...")
            print_tcdb_help()
        elif source == "beckett":
            from .fetch_sports import print_beckett_help

            print("Staging Beckett sports checklists...")
            print_beckett_help()
