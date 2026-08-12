"""Shared paths and the language table used across the pipeline."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
TCGDEX_RAW = DATA_RAW / "tcgdex"
SOURCES = ROOT / "sources"
BUILD = ROOT / "build"
EXPORTS = ROOT / "exports"
DB_PATH = BUILD / "pokemon_tcg.sqlite"

TCGDEX_API = "https://api.tcgdex.net/v2"

# Languages the official Pokemon TCG has been printed in that TCGdex serves.
# region: "western" sets share set identifiers, "asian" sets follow the
# Japanese numbering scheme and are released independently.
LANGUAGES: list[dict[str, str]] = [
    {"code": "en", "name_en": "English", "name_native": "English", "region": "western"},
    {"code": "fr", "name_en": "French", "name_native": "Français", "region": "western"},
    {"code": "de", "name_en": "German", "name_native": "Deutsch", "region": "western"},
    {"code": "es", "name_en": "Spanish", "name_native": "Español", "region": "western"},
    {"code": "it", "name_en": "Italian", "name_native": "Italiano", "region": "western"},
    {"code": "pt", "name_en": "Portuguese", "name_native": "Português", "region": "western"},
    {
        "code": "pt-br",
        "name_en": "Portuguese (Brazil)",
        "name_native": "Português (Brasil)",
        "region": "western",
    },
    {"code": "nl", "name_en": "Dutch", "name_native": "Nederlands", "region": "western"},
    {"code": "pl", "name_en": "Polish", "name_native": "Polski", "region": "western"},
    {"code": "ru", "name_en": "Russian", "name_native": "Русский", "region": "western"},
    {"code": "id", "name_en": "Indonesian", "name_native": "Bahasa Indonesia", "region": "asian"},
    {"code": "th", "name_en": "Thai", "name_native": "ไทย", "region": "asian"},
    {"code": "ja", "name_en": "Japanese", "name_native": "日本語", "region": "asian"},
    {"code": "ko", "name_en": "Korean", "name_native": "한국어", "region": "asian"},
    {
        "code": "zh-tw",
        "name_en": "Chinese (Traditional)",
        "name_native": "繁體中文",
        "region": "asian",
    },
    {
        "code": "zh-cn",
        "name_en": "Chinese (Simplified)",
        "name_native": "简体中文",
        "region": "asian",
    },
]

LANGUAGE_CODES = [lang["code"] for lang in LANGUAGES]
