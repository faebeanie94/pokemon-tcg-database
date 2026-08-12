"""Download every set (with its card list) from the TCGdex API, per language.

One JSON document is written per language: ``data/raw/tcgdex/<lang>.json``.
Storing a single file per language keeps set identifiers that differ only by
case (``sv01`` vs ``SV01``) from colliding on case-insensitive filesystems.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

from .config import LANGUAGE_CODES, TCGDEX_API, TCGDEX_RAW

USER_AGENT = "pokemon-tcg-database/1.0 (+https://github.com/)"
MAX_ATTEMPTS = 5
WORKERS = 8


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return session


def _get(session: requests.Session, url: str) -> Any:
    delay = 2.0
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = session.get(url, timeout=45)
            if response.status_code == 404:
                return None
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(f"HTTP {response.status_code} for {url}")
            response.raise_for_status()
            return response.json()
        except Exception as error:  # noqa: BLE001 - retried below
            last_error = error
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(delay)
                delay *= 2
    raise RuntimeError(f"giving up on {url}") from last_error


def fetch_language(lang: str, session: requests.Session | None = None) -> dict[str, Any]:
    session = session or _session()
    brief_sets = _get(session, f"{TCGDEX_API}/{lang}/sets") or []
    series = _get(session, f"{TCGDEX_API}/{lang}/series") or []

    def load(brief: dict[str, Any]) -> tuple[str, Any]:
        set_id = brief["id"]
        return set_id, _get(session, f"{TCGDEX_API}/{lang}/sets/{set_id}")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(load, brief_sets))

    return {
        "language": lang,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "tcgdex",
        "api": TCGDEX_API,
        "series": series,
        "sets": {set_id: payload for set_id, payload in results if payload},
    }


def fetch_all(languages: list[str] | None = None) -> None:
    languages = languages or LANGUAGE_CODES
    TCGDEX_RAW.mkdir(parents=True, exist_ok=True)
    session = _session()
    for lang in languages:
        payload = fetch_language(lang, session)
        target = TCGDEX_RAW / f"{lang}.json"
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True),
            encoding="utf-8",
        )
        cards = sum(len(s.get("cards") or []) for s in payload["sets"].values())
        print(f"  {lang:<6} {len(payload['sets']):>4} sets  {cards:>7} cards -> {target.name}")
