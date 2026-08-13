"""Load curated sports checklists from ``data/raw/sports/seed.json``.

Sports cards have no public checklist API; seed JSON (and optional xlsx) is the
default ingestion path. See docs/DATA_SOURCES.md.
"""

from __future__ import annotations

import json

from ..config import SPORTS_RAW
from ..normalize import clean_text, parse_date
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "sports_seed"
GAME = "sports"


def load() -> SourceData | None:
    path = SPORTS_RAW / "seed.json"
    if not path.exists():
        # Also accept a repo-root seed for convenience during development.
        from ..config import ROOT

        alt = ROOT / "data" / "raw" / "sports" / "seed.json"
        path = alt if alt.exists() else path
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    data = SourceData(name=SOURCE)

    for set_payload in payload.get("sets") or []:
        set_id = clean_text(set_payload.get("id") or set_payload.get("name"))
        name = clean_text(set_payload.get("name"))
        if not set_id or not name:
            continue
        data.sets.append(
            SetRecord(
                source=SOURCE,
                game=GAME,
                language=clean_text(set_payload.get("language")) or "en",
                source_set_id=set_id,
                name=name,
                name_en=name,
                abbreviation=clean_text(set_payload.get("abbreviation")),
                release_date=parse_date(set_payload.get("release_date")),
                manufacturer=clean_text(set_payload.get("manufacturer")),
                sport=clean_text(set_payload.get("sport")),
                product_year=clean_text(set_payload.get("product_year")),
            )
        )

    for card in payload.get("cards") or []:
        set_id = clean_text(card.get("set_id"))
        number = clean_text(str(card.get("number") or ""))
        name = clean_text(card.get("name") or card.get("display_name"))
        if not set_id or not number or not name:
            continue
        subject = clean_text(card.get("subject_name"))
        parallel = clean_text(card.get("parallel"))
        notations = clean_text(card.get("notations"))
        display = clean_text(card.get("display_name")) or _display(subject or name, notations, parallel, card)
        data.cards.append(
            CardRecord(
                source=SOURCE,
                game=GAME,
                language=clean_text(card.get("language")) or "en",
                source_set_id=set_id,
                number=number,
                name=display,
                name_en=display,
                subject_name=subject,
                parallel=parallel,
                notations=notations,
                serial_number=clean_text(str(card.get("serial_number") or "") or None),
                print_run=int(card["print_run"]) if card.get("print_run") else None,
                display_name=display,
            )
        )

    return data if data.sets else None


def _display(subject: str, notations: str | None, parallel: str | None, card: dict) -> str:
    parts = [subject]
    if notations:
        parts.append(notations.replace(",", " - "))
    if parallel:
        parts.append(parallel)
    serial = card.get("serial_number")
    print_run = card.get("print_run")
    if serial and print_run:
        parts.append(f"{serial}/{print_run}")
    return " - ".join(parts)
