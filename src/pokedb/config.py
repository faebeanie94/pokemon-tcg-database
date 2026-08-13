"""Shared paths, languages, and the games registry."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
TCGDEX_RAW = DATA_RAW / "tcgdex"
TCGCSV_RAW = DATA_RAW / "tcgcsv"
SCRYFALL_RAW = DATA_RAW / "scryfall"
LORCAST_RAW = DATA_RAW / "lorcast"
YGOPRODECK_RAW = DATA_RAW / "ygoprodeck"
GOAGAIN_RAW = DATA_RAW / "goagain"
APITCG_RAW = DATA_RAW / "apitcg"
SPORTS_RAW = DATA_RAW / "sports"
SOURCES = ROOT / "sources"
BUILD = ROOT / "build"
EXPORTS = ROOT / "exports"
DB_PATH = BUILD / "pokemon_tcg.sqlite"

TCGDEX_API = "https://api.tcgdex.net/v2"
TCGCSV_API = "https://tcgcsv.com/tcgplayer"
SCRYFALL_API = "https://api.scryfall.com"
LORCAST_API = "https://api.lorcast.com/v0"
YGOPRODECK_API = "https://db.ygoprodeck.com/api/v7"
GOAGAIN_API = "https://api.goagain.dev"
APITCG_API = "https://apitcg.com/api"

# Games known to the catalog. Loaders set `game` on every record they emit.
GAMES: list[dict[str, str]] = [
    {"code": "pokemon", "name": "Pokémon TCG", "kind": "tcg"},
    {"code": "mtg", "name": "Magic: The Gathering", "kind": "tcg"},
    {"code": "yugioh", "name": "Yu-Gi-Oh!", "kind": "tcg"},
    {"code": "onepiece", "name": "One Piece Card Game", "kind": "tcg"},
    {"code": "lorcana", "name": "Disney Lorcana", "kind": "tcg"},
    {"code": "fleshblood", "name": "Flesh and Blood", "kind": "tcg"},
    {"code": "weiss", "name": "Weiss Schwarz", "kind": "tcg"},
    {"code": "dbz", "name": "Dragon Ball Z TCG", "kind": "tcg"},
    {"code": "dbs", "name": "Dragon Ball Super: Masters", "kind": "tcg"},
    {"code": "dbsfw", "name": "Dragon Ball Super: Fusion World", "kind": "tcg"},
    {"code": "metazoo", "name": "MetaZoo", "kind": "tcg"},
    {"code": "warhammer", "name": "Warhammer Age of Sigmar Champions", "kind": "tcg"},
    {"code": "dicemasters", "name": "Marvel Dice Masters", "kind": "tcg"},
    {"code": "sports", "name": "Sports & Entertainment Cards", "kind": "sports"},
]

# TCGplayer category IDs mirrored by TCGCSV, keyed by our game code.
TCGCSV_CATEGORIES: dict[str, int] = {
    "mtg": 1,
    "yugioh": 2,
    "weiss": 20,
    "dbz": 23,
    "dbs": 27,
    "fleshblood": 62,
    "onepiece": 68,
    "lorcana": 71,
    "metazoo": 66,
    "warhammer": 54,
    "dicemasters": 18,
    "dbsfw": 80,
}

# Languages the catalog accepts. Pokémon-focused entries keep their region
# labels; Scryfall extras and a sports-default English are also listed.
LANGUAGES: list[dict[str, str | None]] = [
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
    # Scryfall / MTG extras
    {"code": "zhs", "name_en": "Chinese (Simplified, MTG)", "name_native": "简体中文", "region": None},
    {"code": "zht", "name_en": "Chinese (Traditional, MTG)", "name_native": "繁體中文", "region": None},
    {"code": "he", "name_en": "Hebrew", "name_native": "עברית", "region": None},
    {"code": "la", "name_en": "Latin", "name_native": "Latina", "region": None},
    {"code": "grc", "name_en": "Ancient Greek", "name_native": "Ἑλληνική", "region": None},
    {"code": "ar", "name_en": "Arabic", "name_native": "العربية", "region": None},
    {"code": "sa", "name_en": "Sanskrit", "name_native": "संस्कृतम्", "region": None},
    {"code": "ph", "name_en": "Phyrexian", "name_native": "Phyrexian", "region": None},
    {"code": "qya", "name_en": "Quenya", "name_native": "Quenya", "region": None},
    {"code": "dw", "name_en": "Dwarvish", "name_native": "Dwarvish", "region": None},
    # Language-neutral: sports and other catalogs with no translation axis.
    # Sports rows still use 'en' when the printed label is English.
    {"code": "und", "name_en": "Undetermined", "name_native": None, "region": None},
]

LANGUAGE_CODES = [lang["code"] for lang in LANGUAGES]
GAME_CODES = [game["code"] for game in GAMES]
