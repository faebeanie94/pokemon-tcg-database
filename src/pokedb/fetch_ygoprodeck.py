"""Fetch YGOPRODeck cardinfo dumps per language."""

from __future__ import annotations

import json
import urllib.request

from .config import YGOPRODECK_API, YGOPRODECK_RAW

LANGUAGES = ("en", "fr", "de", "it", "pt")


def fetch_all(languages: list[str] | None = None) -> dict[str, int]:
    YGOPRODECK_RAW.mkdir(parents=True, exist_ok=True)
    selected = languages or list(LANGUAGES)
    counts: dict[str, int] = {}
    for language in selected:
        url = f"{YGOPRODECK_API}/cardinfo.php"
        if language != "en":
            url += f"?language={language}"
        print(f"  YGOPRODeck {language}...")
        with urllib.request.urlopen(url, timeout=180) as response:
            payload = json.loads(response.read().decode("utf-8"))
        (YGOPRODECK_RAW / f"{language}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        cards = payload.get("data", payload) if isinstance(payload, dict) else payload
        counts[language] = len(cards)
        print(f"    {counts[language]} cards")
    return counts
