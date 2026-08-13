"""Download Scryfall bulk card data into ``data/raw/scryfall/``."""

from __future__ import annotations

import json
import urllib.request

from .config import SCRYFALL_API, SCRYFALL_RAW


def fetch_all(*, bulk_type: str = "all_cards") -> str:
    """Download a Scryfall bulk file. Returns the local path written."""
    SCRYFALL_RAW.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{SCRYFALL_API}/bulk-data", timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    entry = next((item for item in payload.get("data", []) if item.get("type") == bulk_type), None)
    if entry is None:
        raise SystemExit(f"Scryfall bulk type '{bulk_type}' not found")

    download_uri = entry["download_uri"]
    # Prefer gzip when the URI ends in .gz; otherwise write jsonl.
    suffix = ".jsonl.gz" if download_uri.endswith(".gz") else ".jsonl"
    out = SCRYFALL_RAW / f"{bulk_type}{suffix}"
    print(f"  Downloading {bulk_type} ({entry.get('size') or '?'} bytes)...")
    urllib.request.urlretrieve(download_uri, out)
    return str(out)
