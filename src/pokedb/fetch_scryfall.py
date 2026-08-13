"""Download Scryfall bulk card data into ``data/raw/scryfall/``."""

from __future__ import annotations

import json
import urllib.request

from .config import SCRYFALL_API, SCRYFALL_RAW

_UA = "Mozilla/5.0 (compatible; pokedb/1.0; +https://github.com/)"


def fetch_all(*, bulk_type: str = "default_cards") -> str:
    """Download a Scryfall bulk file. Returns the local path written.

    Defaults to ``default_cards`` (English printings) rather than ``all_cards``
    (hundreds of MB of every language) so opt-in Magic fetches stay usable.
    Pass ``bulk_type='all_cards'`` for the full multilingual dump.
    """
    SCRYFALL_RAW.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        f"{SCRYFALL_API}/bulk-data",
        headers={"User-Agent": _UA, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    entry = next((item for item in payload.get("data", []) if item.get("type") == bulk_type), None)
    if entry is None:
        raise SystemExit(f"Scryfall bulk type '{bulk_type}' not found")

    download_uri = (
        entry.get("download_uri")
        or entry.get("jsonl_download_uri")
        or entry.get("uri")
    )
    if not download_uri:
        raise SystemExit(f"Scryfall bulk entry for '{bulk_type}' has no download URI")

    # Prefer gzip when the URI ends in .gz; otherwise write jsonl.
    suffix = ".jsonl.gz" if str(download_uri).endswith(".gz") else ".jsonl"
    out = SCRYFALL_RAW / f"{bulk_type}{suffix}"
    size = entry.get("compressed_size") or entry.get("size") or "?"
    print(f"  Downloading {bulk_type} ({size} bytes)...")
    download_req = urllib.request.Request(download_uri, headers={"User-Agent": _UA})
    with urllib.request.urlopen(download_req, timeout=600) as response, out.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    return str(out)
