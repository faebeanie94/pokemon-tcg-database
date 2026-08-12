"""Command line entry point: ``python -m pokedb <command>``."""

from __future__ import annotations

import argparse

from .config import DB_PATH, LANGUAGE_CODES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pokedb", description="Build the Pokemon TCG multi-language card database."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="download the latest set/card data from TCGdex")
    fetch.add_argument(
        "--language",
        action="append",
        choices=LANGUAGE_CODES,
        help="limit to specific languages (repeatable, default: all)",
    )

    subparsers.add_parser("build", help="merge every source into the SQLite database")
    export = subparsers.add_parser("export", help="write the Excel workbook and CSVs")
    export.add_argument("--no-csv", action="store_true", help="only write the Excel workbook")
    subparsers.add_parser("report", help="print coverage and source disagreements")
    subparsers.add_parser("verify", help="check the input spreadsheets against the API data")
    update = subparsers.add_parser(
        "update", help="fetch, build, export and report - the usual refresh"
    )
    update.add_argument("--no-csv", action="store_true", help="only write the Excel workbook")

    args = parser.parse_args(argv)
    command = args.command

    if command in {"fetch", "update"}:
        from .fetch_tcgdex import fetch_all

        print("Fetching TCGdex data...")
        fetch_all(getattr(args, "language", None))

    if command in {"build", "update"}:
        from .build import build

        print("Building database...")
        stats = build()
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
