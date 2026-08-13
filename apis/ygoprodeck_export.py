#!/usr/bin/env python3
"""
Export Yu-Gi-Oh! card data from YGOPRODeck (en/fr/de/it/pt).

Usage:
    python3 ygoprodeck_export.py
    python3 ygoprodeck_export.py --language fr --out-dir .
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

YGOPRODECK_API = "https://db.ygoprodeck.com/api/v7"
LANGUAGES = ("en", "fr", "de", "it", "pt")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", action="append", choices=LANGUAGES)
    parser.add_argument("--out-dir", default=".", help="directory for per-language JSON")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for language in args.language or LANGUAGES:
        url = f"{YGOPRODECK_API}/cardinfo.php"
        if language != "en":
            url += f"?language={language}"
        print(f"Fetching {language}...")
        with urllib.request.urlopen(url, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))
        path = out_dir / f"ygoprodeck_{language}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        cards = payload.get("data", payload) if isinstance(payload, dict) else payload
        print(f"  {len(cards)} cards -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
