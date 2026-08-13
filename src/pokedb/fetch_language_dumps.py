"""Stage non-English publisher dumps that have no stable free API.

Covers the documented Phase 4 language gaps:

- Weiss Schwarz Japanese (Bushiroad) → ``data/raw/weiss_jp/``
- Yu-Gi-Oh! OCG Japanese → ``data/raw/ygo_ocg/``
- Lorcana non-English → ``data/raw/lorcana_i18n/``

Each dump is operator-supplied JSON (offline scrape / licensed export). Live
HTML scrapes are not automated — same rationale as TCDB / Bandai JP.

Usage::

    PYTHONPATH=src python3 -m pokedb.fetch_language_dumps --help
    PYTHONPATH=src python3 -m pokedb.fetch_language_dumps --target weiss_jp --from-file dump.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import DATA_RAW

TARGETS = {
    "weiss_jp": {
        "game": "weiss",
        "default_language": "ja",
        "dir": DATA_RAW / "weiss_jp",
        "notes": "Bushiroad JP Weiss Schwarz sets absent from TCGCSV (EN-only).",
    },
    "ygo_ocg": {
        "game": "yugioh",
        "default_language": "ja",
        "dir": DATA_RAW / "ygo_ocg",
        "notes": "YGOPRODeck covers en/fr/de/it/pt only; OCG Japanese needs Konami DB / community dump.",
    },
    "lorcana_i18n": {
        "game": "lorcana",
        "default_language": "fr",
        "dir": DATA_RAW / "lorcana_i18n",
        "notes": "Lorcast is EN-centric; drop Ravensburger regional dumps when available.",
    },
}


def print_help() -> None:
    lines = [
        "Language-gap dump staging",
        "=========================",
        "",
        "Drop normalized sets.json + cards.json (or pass --from-file) under:",
        "",
    ]
    for key, meta in TARGETS.items():
        lines.append(f"  {meta['dir']}  ({meta['game']}, default lang {meta['default_language']})")
        lines.append(f"    {meta['notes']}")
        lines.append("")
    lines.append(
        "Normalize:\n"
        "  PYTHONPATH=src python3 -m pokedb.fetch_language_dumps "
        "--target weiss_jp --from-file dump.json"
    )
    print("\n".join(lines))


def normalize(payload: dict, *, default_language: str) -> tuple[list[dict], list[dict]]:
    sets: list[dict] = []
    for item in payload.get("sets") or []:
        if not isinstance(item, dict):
            continue
        set_id = str(item.get("id") or item.get("set_id") or item.get("code") or "").strip()
        name = str(item.get("name") or item.get("set_name") or set_id).strip()
        if not set_id and not name:
            continue
        sets.append(
            {
                "id": set_id or name,
                "name": name or set_id,
                "name_en": (item.get("name_en") or "").strip() or None,
                "abbreviation": (item.get("abbreviation") or item.get("code") or "").strip()
                or None,
                "release_date": (item.get("release_date") or "").strip() or None,
                "language": (item.get("language") or default_language).strip() or default_language,
            }
        )

    cards: list[dict] = []
    for item in payload.get("cards") or []:
        if not isinstance(item, dict):
            continue
        set_id = str(item.get("set_id") or item.get("set") or "").strip()
        number = str(item.get("number") or item.get("card_number") or "").strip()
        name = str(item.get("name") or item.get("printed_name") or "").strip()
        if not set_id or not number or not name:
            continue
        cards.append(
            {
                "set_id": set_id,
                "number": number,
                "name": name,
                "name_en": (item.get("name_en") or "").strip() or None,
                "rarity": (item.get("rarity") or "").strip() or None,
                "image_url": (item.get("image_url") or "").strip() or None,
                "language": (item.get("language") or default_language).strip() or default_language,
            }
        )
    return sets, cards


def write_dump(target: str, sets: list[dict], cards: list[dict]) -> Path:
    meta = TARGETS[target]
    out = meta["dir"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "sets.json").write_text(json.dumps(sets, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "cards.json").write_text(
        json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=sorted(TARGETS), help="which language gap to stage")
    parser.add_argument("--from-file", type=Path, help="operator JSON dump to normalize")
    args = parser.parse_args(argv)

    if args.target is None or args.from_file is None:
        print_help()
        return 0 if args.from_file is None else 1

    payload = json.loads(args.from_file.read_text(encoding="utf-8"))
    sets, cards = normalize(payload, default_language=TARGETS[args.target]["default_language"])
    path = write_dump(args.target, sets, cards)
    print(f"wrote {len(sets)} sets / {len(cards)} cards under {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
