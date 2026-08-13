"""Load Beckett-shaped sports checklist dumps from ``data/raw/beckett/``.

Expects one ``*.json`` per article / release written by
``apis/beckett_fetch.py`` (or a hand-normalized dump):

    {
      "slug": "2024-panini-flawless-wwe-checklist",
      "set": {
        "id": "2024-panini-flawless-wwe",
        "name": "2024 PANINI FLAWLESS WWE",
        "manufacturer": "Panini",
        "sport": "wrestling",
        "product_year": "2024"
      },
      "cards": [
        {
          "number": "SSL-SM",
          "player": "SHAWN MICHAELS",
          "notations": "AUTO",
          "parallel": "RUBY REF",
          "serial_number": "09",
          "print_run": 15
        }
      ]
    }
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import BECKETT_RAW
from ..normalize import clean_text, parse_date, slugify
from ..records import CardRecord, SetRecord, SourceData

SOURCE = "beckett"
GAME = "sports"


def load() -> SourceData | None:
    if not BECKETT_RAW.exists():
        return None

    files = sorted(BECKETT_RAW.glob("*.json"))
    if not files:
        return None

    data = SourceData(name=SOURCE)
    for path in files:
        payload = _read(path)
        if not payload:
            continue
        set_payload = payload.get("set") or {}
        set_id = _ensure_set(data, set_payload, path.stem)
        if not set_id:
            continue
        for card in payload.get("cards") or []:
            record = _card_record(card, set_id)
            if record is not None:
                data.cards.append(record)

    return data if data.sets or data.cards else None


def _read(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _ensure_set(data: SourceData, payload: dict, fallback_slug: str) -> str | None:
    name = clean_text(payload.get("name") or payload.get("set_name"))
    set_id = clean_text(payload.get("id") or payload.get("set_id")) or (
        slugify(name) if name else slugify(fallback_slug)
    )
    if not set_id:
        return None
    if not name:
        name = set_id
    data.sets.append(
        SetRecord(
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
    )
    return set_id


def _card_record(card: dict, set_id: str) -> CardRecord | None:
    number = clean_text(str(card.get("number") or ""))
    subject = clean_text(
        card.get("player") or card.get("subject_name") or card.get("subject")
    )
    display = clean_text(card.get("display_name") or card.get("name"))
    if not number or not (subject or display):
        return None

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
