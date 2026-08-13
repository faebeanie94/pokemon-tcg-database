#!/usr/bin/env python3
"""Normalize / stage Beckett checklist articles into ``data/raw/beckett/``.

Beckett checklist pages are HTML articles without a public API. This adapter
accepts an operator-supplied JSON dump (hand-extracted or scraped offline) and
writes one file per release for the ``beckett`` loader.

Usage:

    python3 apis/beckett_fetch.py --from-file path/to/article.json
    python3 apis/beckett_fetch.py --from-file article.json --slug 2024-panini-flawless-wwe

Live scraping is not implemented — markup and ToS change often. Prefer curated
``sports_database.xlsx`` / ``sports_cards.xlsx`` when dumps go stale.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw" / "beckett"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "checklist"


def normalize(payload: dict, slug: str | None = None) -> dict:
    set_payload = payload.get("set") if isinstance(payload.get("set"), dict) else {}
    if not set_payload and payload.get("name"):
        set_payload = {
            "id": payload.get("id"),
            "name": payload.get("name"),
            "manufacturer": payload.get("manufacturer"),
            "sport": payload.get("sport"),
            "product_year": payload.get("product_year") or payload.get("season"),
            "release_date": payload.get("release_date"),
        }

    name = (set_payload.get("name") or set_payload.get("set_name") or "").strip()
    set_id = (set_payload.get("id") or set_payload.get("set_id") or "").strip()
    if not set_id and name:
        set_id = _slugify(name)
    resolved_slug = slug or payload.get("slug") or set_id or _slugify(name or "checklist")

    cards = []
    for item in payload.get("cards") or []:
        if not isinstance(item, dict):
            continue
        number = str(item.get("number") or "").strip()
        player = (
            item.get("player") or item.get("subject_name") or item.get("subject") or ""
        ).strip()
        if not number or not player:
            continue
        cards.append(
            {
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

    return {
        "slug": resolved_slug,
        "set": {
            "id": set_id or resolved_slug,
            "name": name or set_id or resolved_slug,
            "manufacturer": (set_payload.get("manufacturer") or "").strip() or None,
            "sport": (set_payload.get("sport") or "").strip() or None,
            "product_year": (
                set_payload.get("product_year")
                or set_payload.get("season")
                or set_payload.get("year")
                or ""
            ).strip()
            or None,
            "release_date": (set_payload.get("release_date") or "").strip() or None,
            "language": (set_payload.get("language") or "en").strip() or "en",
        },
        "cards": cards,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-file", required=True, type=Path)
    parser.add_argument("--slug", type=str, default=None)
    args = parser.parse_args(argv)

    if not args.from_file.exists():
        print(f"missing input: {args.from_file}", file=sys.stderr)
        return 1

    payload = json.loads(args.from_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        print("input JSON must be an object", file=sys.stderr)
        return 1

    normalized = normalize(payload, slug=args.slug)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{normalized['slug']}.json"
    out_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"wrote {out_path}: set={normalized['set']['name']!r}, "
        f"{len(normalized['cards'])} cards"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
