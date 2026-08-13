"""Load TCDB-shaped sports checklist dumps from ``data/raw/tcdb/``.

Expects one or more ``*.json`` files written by ``apis/tcdb_fetch.py`` (or a
hand-normalized dump) with this shape:

    {
      "sets": [
        {
          "id": "2024-topps-chrome-football",
          "name": "2024 TOPPS CHROME FOOTBALL",
          "manufacturer": "Topps",
          "sport": "football",
          "product_year": "2024",
          "release_date": "2024-09-01"
        }
      ],
      "cards": [
        {
          "set_id": "2024-topps-chrome-football",
          "number": "1",
          "player": "PATRICK MAHOMES",
          "notations": "RC",
          "parallel": "REFRACTOR"
        }
      ]
    }

Curated ``sports_database.xlsx`` wins on set names; TCDB fills card completeness.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import TCDB_RAW
from ..normalize import clean_text, parse_date, slugify
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "tcdb"
GAME = "sports"


def load() -> SourceData | None:
    if not TCDB_RAW.exists():
        return None

    files = sorted(TCDB_RAW.glob("*.json"))
    if not files:
        return None

    data = SourceData(name=SOURCE)
    seen_sets: set[str] = set()

    for path in files:
        payload = _read(path)
        if not payload:
            continue
        for set_payload in payload.get("sets") or []:
            set_id, record = _set_record(set_payload)
            if not set_id or set_id in seen_sets:
                continue
            seen_sets.add(set_id)
            data.sets.append(record)

        for card in payload.get("cards") or []:
            record = _card_record(card, seen_sets, data)
            if record is not None:
                data.cards.append(record)

    return data if data.sets or data.cards else None


def _read(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _set_record(payload: dict) -> tuple[str | None, SetRecord | None]:
    name = clean_text(payload.get("name") or payload.get("set_name"))
    set_id = clean_text(payload.get("id") or payload.get("set_id")) or (
        slugify(name) if name else None
    )
    if not set_id or not name:
        return None, None
    return set_id, SetRecord(
        source=SOURCE,
        game=GAME,
        language=clean_text(payload.get("language")) or "en",
        source_set_id=set_id,
        name=name,
        name_en=name,
        manufacturer=clean_text(payload.get("manufacturer")),
        sport=clean_text(payload.get("sport")),
        product_year=clean_text(
            payload.get("product_year") or payload.get("season") or payload.get("year")
        ),
        release_date=parse_date(payload.get("release_date")),
    )


def _card_record(
    card: dict, seen_sets: set[str], data: SourceData
) -> CardRecord | None:
    set_id = clean_text(card.get("set_id"))
    number = clean_text(str(card.get("number") or ""))
    subject = clean_text(
        card.get("player") or card.get("subject_name") or card.get("subject")
    )
    display = clean_text(card.get("display_name") or card.get("name"))
    if not set_id or not number or not (subject or display):
        return None

    if set_id not in seen_sets:
        seen_sets.add(set_id)
        data.sets.append(
            SetRecord(
                source=SOURCE,
                game=GAME,
                language="en",
                source_set_id=set_id,
                name=set_id,
                name_en=set_id,
            )
        )

    notations = clean_text(card.get("notations") or card.get("variant_tags"))
    parallel = clean_text(card.get("parallel"))
    serial = clean_text(str(card.get("serial_number") or "") or None)
    print_run = card.get("print_run") or card.get("serial_total")
    print_run_int = int(print_run) if print_run not in (None, "") else None
    label = display or _label(subject or "", notations, parallel, serial, print_run_int)

    return CardRecord(
        source=SOURCE,
        game=GAME,
        language=clean_text(card.get("language")) or "en",
        source_set_id=set_id,
        number=number,
        name=label,
        name_en=label,
        subject_name=subject,
        parallel=parallel,
        notations=notations,
        serial_number=serial,
        print_run=print_run_int,
        display_name=label,
    )


def _label(
    subject: str,
    notations: str | None,
    parallel: str | None,
    serial: str | None,
    print_run: int | None,
) -> str:
    parts = [subject] if subject else []
    if notations:
        parts.append(notations.replace(",", " - "))
    if parallel:
        parts.append(parallel)
    if serial and print_run:
        parts.append(f"{serial}/{print_run}")
    return " - ".join(parts) if parts else subject
