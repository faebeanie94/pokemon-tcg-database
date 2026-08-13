#!/usr/bin/env python3
"""Normalize / stage TCDB sports checklists into ``data/raw/tcdb/``.

There is no stable public TCDB API. This adapter accepts an operator-supplied
JSON dump (scraped offline, exported, or hand-built) and writes the canonical
shape the ``tcdb`` loader expects.

Usage:

    python3 apis/tcdb_fetch.py --from-file path/to/dump.json
    python3 apis/tcdb_fetch.py --from-file dump.json --sport football --out football.json

Live HTML scraping is intentionally not implemented here — TCDB terms and markup
change often. Prefer a commercial catalog or curated xlsx when dumps go stale.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw" / "tcdb"


def normalize(payload: dict) -> dict:
    sets = []
    for item in payload.get("sets") or []:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or item.get("set_name") or "").strip()
        set_id = (item.get("id") or item.get("set_id") or "").strip()
        if not name and not set_id:
            continue
        sets.append(
            {
                "id": set_id or name.lower().replace(" ", "-"),
                "name": name or set_id,
                "manufacturer": (item.get("manufacturer") or "").strip() or None,
                "sport": (item.get("sport") or "").strip() or None,
                "product_year": (
                    item.get("product_year") or item.get("season") or item.get("year") or ""
                ).strip()
                or None,
                "release_date": (item.get("release_date") or "").strip() or None,
                "language": (item.get("language") or "en").strip() or "en",
            }
        )

    cards = []
    for item in payload.get("cards") or []:
        if not isinstance(item, dict):
            continue
        number = str(item.get("number") or "").strip()
        player = (
            item.get("player") or item.get("subject_name") or item.get("subject") or ""
        ).strip()
        set_id = (item.get("set_id") or "").strip()
        if not number or not player or not set_id:
            continue
        cards.append(
            {
                "set_id": set_id,
                "number": number,
                "player": player,
                "notations": (item.get("notations") or item.get("variant_tags") or "").strip()
                or None,
                "parallel": (item.get("parallel") or "").strip() or None,
                "serial_number": str(item.get("serial_number") or "").strip() or None,
                "print_run": item.get("print_run") or item.get("serial_total"),
                "display_name": (item.get("display_name") or item.get("name") or "").strip()
                or None,
                "language": (item.get("language") or "en").strip() or "en",
            }
        )

    return {"sets": sets, "cards": cards}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-file",
        required=True,
        type=Path,
        help="JSON dump to normalize into data/raw/tcdb/",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="output filename under data/raw/tcdb/ (default: stem of --from-file)",
    )
    parser.add_argument(
        "--sport",
        type=str,
        default=None,
        help="optional sport tag applied to sets missing one",
    )
    args = parser.parse_args(argv)

    if not args.from_file.exists():
        print(f"missing input: {args.from_file}", file=sys.stderr)
        return 1

    payload = json.loads(args.from_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        print("input JSON must be an object with sets/cards", file=sys.stderr)
        return 1

    normalized = normalize(payload)
    if args.sport:
        for set_row in normalized["sets"]:
            set_row["sport"] = set_row.get("sport") or args.sport

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_name = args.out or f"{args.from_file.stem}.json"
    out_path = OUT_DIR / out_name
    out_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}: {len(normalized['sets'])} sets, {len(normalized['cards'])} cards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
