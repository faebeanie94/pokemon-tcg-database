"""Fetch YGOPRODeck cardinfo dumps per language."""

from __future__ import annotations

import json
import urllib.request

from .config import YGOPRODECK_API, YGOPRODECK_RAW

LANGUAGES = ("en", "fr", "de", "it", "pt")

# YGOPRODeck returns 403 without a browser-like User-Agent.
_UA = "Mozilla/5.0 (compatible; pokedb/1.0; +https://github.com/)"


def _get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all(languages: list[str] | None = None) -> dict[str, int]:
    YGOPRODECK_RAW.mkdir(parents=True, exist_ok=True)
    selected = languages or list(LANGUAGES)
    counts: dict[str, int] = {}
    for language in selected:
        url = f"{YGOPRODECK_API}/cardinfo.php"
        if language != "en":
            url += f"?language={language}"
        print(f"  YGOPRODeck {language}...")
        payload = _get_json(url)
        (YGOPRODECK_RAW / f"{language}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        cards = payload.get("data", payload) if isinstance(payload, dict) else payload
        counts[language] = len(cards)
        print(f"    {counts[language]} cards")
    return counts
