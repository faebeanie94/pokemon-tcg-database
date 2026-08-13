#!/usr/bin/env python3
"""Compose dump workbooks into one SQLite catalog with duplicates removed.

Reads API / marketplace xlsx dumps from the repo root and the parent folder,
normalizes them onto a shared card identity, and writes:

    build/composed_catalog.sqlite   — best file for a database
    exports/composed_cards.csv.gz   — same rows for spreadsheets

Identity is ``game:language:set#number[#variant]``. When two dumps describe the
same printing, the higher-ranked source keeps the row and later sources only
fill blank fields.
"""

from __future__ import annotations

import gzip
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pokedb.config import BUILD, EXPORTS  # noqa: E402
from pokedb.normalize import clean_text, normalize_code, normalize_name, slugify  # noqa: E402

DUMP_DIRS = (
    ROOT.parent,
    ROOT,
    ROOT / "sources",
)

# Lower rank wins. Dedicated catalogs beat marketplace dumps.
SOURCE_RANK = {
    "scryfall": 10,
    "tcgdex": 10,
    "ygoprodeck": 10,
    "pikaqian": 12,
    "sports_database": 12,
    "sports_cards": 12,
    "apitcg": 18,
    "digimoncard": 18,
    "optcgapi": 22,
    "onepiece": 28,
    "pokemontcgio": 30,
    "pokewallet": 40,
    "cardtrader": 55,
}

GAME_ALIASES = {
    "magic: the gathering": "mtg",
    "magic:the gathering": "mtg",
    "magic": "mtg",
    "pokemon": "pokemon",
    "pokémon": "pokemon",
    "pokémon tcg": "pokemon",
    "yu-gi-oh!": "yugioh",
    "yu-gi-oh": "yugioh",
    "yugioh": "yugioh",
    "one piece": "onepiece",
    "one piece card game": "onepiece",
    "disney lorcana": "lorcana",
    "lorcana": "lorcana",
    "flesh and blood": "fleshblood",
    "digimon": "digimon",
    "dragon ball super": "dbs",
    "dragon ball fusion": "dbsfw",
    "dragon ball super: fusion world": "dbsfw",
    "dragon ball super fusion world": "dbsfw",
    "union arena": "unionarena",
    "gundam": "gundam",
    "riftbound | league of legends": "riftbound",
    "riftbound": "riftbound",
    "cardfight!! vanguard": "vanguard",
    "vanguard": "vanguard",
    "star wars unlimited": "starwars",
    "star wars": "starwars",
    "sorcery: contested realm": "sorcery",
    "sorcery": "sorcery",
    "sports & entertainment cards": "sports",
    "sports": "sports",
}

LANG_ALIASES = {
    "en": "en",
    "eng": "en",
    "english": "en",
    "fr": "fr",
    "fre": "fr",
    "french": "fr",
    "de": "de",
    "ger": "de",
    "german": "de",
    "es": "es",
    "spa": "es",
    "spanish": "es",
    "it": "it",
    "ita": "it",
    "italian": "it",
    "pt": "pt",
    "por": "pt",
    "portuguese": "pt",
    "pt-br": "pt-br",
    "portuguese (brazil)": "pt-br",
    "ja": "ja",
    "jp": "ja",
    "jap": "ja",
    "jpn": "ja",
    "japanese": "ja",
    "ko": "ko",
    "kr": "ko",
    "korean": "ko",
    "zh-cn": "zh-cn",
    "zh-tw": "zh-tw",
    "zhs": "zhs",
    "zht": "zht",
    "chinese (simplified)": "zh-cn",
    "chinese (traditional)": "zh-tw",
    "id": "id",
    "th": "th",
    "nl": "nl",
    "ru": "ru",
    "pl": "pl",
}

SCHEMA = """
CREATE TABLE cards (
    identity    TEXT PRIMARY KEY,
    game        TEXT NOT NULL,
    language    TEXT NOT NULL,
    set_name    TEXT,
    set_code    TEXT,
    number      TEXT,
    name        TEXT NOT NULL,
    name_en     TEXT,
    rarity      TEXT,
    card_type   TEXT,
    variant     TEXT,
    image_url   TEXT,
    source      TEXT NOT NULL,
    source_rank INTEGER NOT NULL
);
CREATE INDEX idx_composed_game ON cards (game, language);
CREATE INDEX idx_composed_set  ON cards (game, set_code, number);

CREATE TABLE compose_info (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

COLUMNS = (
    "identity",
    "game",
    "language",
    "set_name",
    "set_code",
    "number",
    "name",
    "name_en",
    "rarity",
    "card_type",
    "variant",
    "image_url",
    "source",
    "source_rank",
)


def locate(filename: str) -> Path | None:
    for folder in DUMP_DIRS:
        path = folder / filename
        if path.exists() and path.stat().st_size > 200:
            return path
    return None


def game_code(value: object) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return GAME_ALIASES.get(text.lower())


def language_code(value: object, default: str = "en") -> str:
    text = clean_text(value)
    if not text:
        return default
    return LANG_ALIASES.get(text.lower(), text.lower()[:8])


def identity(
    game: str,
    language: str,
    set_code: str | None,
    set_name: str | None,
    number: str | None,
    name: str,
    variant: str | None,
) -> str:
    set_key = normalize_code(set_code) or normalize_name(set_name) or "set"
    num_key = normalize_code(number) or (number.lower() if number else "")
    var_key = normalize_name(variant) or ""
    if num_key:
        key = f"{game}:{language}:{set_key}#{num_key}"
    else:
        key = f"{game}:{language}:{set_key}#{normalize_name(name) or slugify(name)}"
    return f"{key}#{var_key}" if var_key else key


def row(
    *,
    source: str,
    game: str,
    name: str,
    language: object = "en",
    set_name: object = None,
    set_code: object = None,
    number: object = None,
    name_en: object = None,
    rarity: object = None,
    card_type: object = None,
    variant: object = None,
    image_url: object = None,
) -> dict | None:
    name = clean_text(name)
    if not name or not game:
        return None
    language = language_code(language)
    set_name = clean_text(set_name)
    set_code = clean_text(set_code)
    number = clean_text(number)
    variant = clean_text(variant)
    return {
        "identity": identity(game, language, set_code, set_name, number, name, variant),
        "game": game,
        "language": language,
        "set_name": set_name,
        "set_code": set_code,
        "number": number,
        "name": name,
        "name_en": clean_text(name_en) or (name if language == "en" else None),
        "rarity": clean_text(rarity),
        "card_type": clean_text(card_type),
        "variant": variant,
        "image_url": clean_text(image_url),
        "source": source,
        "source_rank": SOURCE_RANK.get(source, 80),
    }


def iter_excel(path: Path, sheets: list[str] | None = None):
    import pandas as pd

    frames = pd.read_excel(path, sheet_name=None if sheets is None else sheets, dtype=object)
    if isinstance(frames, dict):
        yield from frames.items()
    else:
        yield path.stem, frames


def from_records(frame, source: str, mapper) -> list[dict]:
    rows: list[dict] = []
    for record in frame.to_dict(orient="records"):
        mapped = mapper(record)
        if mapped:
            rows.append(mapped)
    return rows


def load_scryfall(path: Path) -> list[dict]:
    rows: list[dict] = []
    for _sheet, frame in iter_excel(path):
        for rec in frame.to_dict(orient="records"):
            mapped = row(
                source="scryfall",
                game="mtg",
                language=rec.get("lang"),
                set_name=rec.get("set_name"),
                set_code=rec.get("set_code"),
                number=rec.get("collector_number"),
                name=rec.get("name"),
                rarity=rec.get("rarity"),
                card_type=rec.get("type_line"),
                image_url=rec.get("image_normal") or rec.get("image_large"),
            )
            if mapped:
                rows.append(mapped)
    return rows


def load_tcgdex(path: Path) -> list[dict]:
    rows: list[dict] = []
    for sheet, frame in iter_excel(path, sheets=None):
        if str(sheet).lower() == "sets":
            continue
        for rec in frame.to_dict(orient="records"):
            mapped = row(
                source="tcgdex",
                game="pokemon",
                language=rec.get("language"),
                set_name=rec.get("set_name"),
                set_code=rec.get("set_abbreviation") or rec.get("set_id"),
                number=rec.get("card_number"),
                name=rec.get("name"),
                name_en=rec.get("english_name"),
            )
            if mapped:
                rows.append(mapped)
    return rows


def load_pikaqian(path: Path) -> list[dict]:
    import pandas as pd

    sheets = pd.read_excel(path, sheet_name=None, dtype=object)
    sets = {}
    if "Sets" in sheets:
        for rec in sheets["Sets"].to_dict(orient="records"):
            sid = clean_text(rec.get("id"))
            if sid:
                sets[sid] = rec
    rows: list[dict] = []
    cards = sheets.get("Cards")
    if cards is None:
        return rows
    for rec in cards.to_dict(orient="records"):
        set_row = sets.get(clean_text(rec.get("card_set_id")) or "", {})
        mapped = row(
            source="pikaqian",
            game="pokemon",
            language="zh-cn",
            set_name=set_row.get("local_name") or set_row.get("name") or rec.get("card_set_id"),
            set_code=rec.get("card_set_id"),
            number=rec.get("card_number"),
            name=rec.get("local_name") or rec.get("name"),
            name_en=rec.get("name"),
            rarity=rec.get("rarity_label") or rec.get("rarity"),
            card_type=rec.get("card_type"),
            variant=rec.get("variant"),
            image_url=rec.get("image_url"),
        )
        if mapped:
            rows.append(mapped)
    return rows


def load_pokemontcgio(path: Path) -> list[dict]:
    rows: list[dict] = []
    for _sheet, frame in iter_excel(path):
        for rec in frame.to_dict(orient="records"):
            mapped = row(
                source="pokemontcgio",
                game="pokemon",
                set_name=rec.get("set_name"),
                number=rec.get("number"),
                name=rec.get("name"),
                rarity=rec.get("rarity"),
                card_type=rec.get("supertype"),
                image_url=rec.get("image_large") or rec.get("image_small"),
            )
            if mapped:
                rows.append(mapped)
    return rows


def load_pokewallet(path: Path) -> list[dict]:
    rows: list[dict] = []
    for _sheet, frame in iter_excel(path):
        for rec in frame.to_dict(orient="records"):
            number = clean_text(rec.get("card_number"))
            if number and "/" in number:
                number = number.split("/", 1)[0]
            mapped = row(
                source="pokewallet",
                game="pokemon",
                language=rec.get("set_language"),
                set_name=rec.get("set_name"),
                set_code=rec.get("set_code"),
                number=number,
                name=rec.get("clean_name") or rec.get("name"),
                rarity=rec.get("rarity"),
                card_type=rec.get("card_type"),
            )
            if mapped:
                rows.append(mapped)
    return rows


def load_ygoprodeck(path: Path) -> list[dict]:
    rows: list[dict] = []
    for _sheet, frame in iter_excel(path):
        for rec in frame.to_dict(orient="records"):
            set_code = clean_text(rec.get("set_code"))
            mapped = row(
                source="ygoprodeck",
                game="yugioh",
                set_name=rec.get("set_name"),
                set_code=set_code.split("-")[0] if set_code and "-" in set_code else set_code,
                number=set_code,
                name=rec.get("name"),
                rarity=rec.get("set_rarity"),
                card_type=rec.get("type"),
            )
            if mapped:
                rows.append(mapped)
    return rows


def load_onepiece(path: Path) -> list[dict]:
    rows: list[dict] = []
    for _sheet, frame in iter_excel(path):
        for rec in frame.to_dict(orient="records"):
            mapped = row(
                source="onepiece",
                game="onepiece",
                language=rec.get("language"),
                set_name=rec.get("set_name"),
                set_code=rec.get("set_code"),
                number=rec.get("card_number"),
                name=rec.get("clean_name") or rec.get("name"),
                rarity=rec.get("rarity"),
                card_type=rec.get("card_type"),
                variant=rec.get("variant"),
            )
            if mapped:
                rows.append(mapped)
    return rows


def load_optcgapi(path: Path) -> list[dict]:
    rows: list[dict] = []
    for _sheet, frame in iter_excel(path):
        for rec in frame.to_dict(orient="records"):
            mapped = row(
                source="optcgapi",
                game="onepiece",
                set_name=rec.get("set_name"),
                set_code=rec.get("set_id"),
                number=rec.get("card_set_id"),
                name=rec.get("card_name"),
                rarity=rec.get("rarity"),
                card_type=rec.get("card_type"),
                image_url=rec.get("card_image"),
            )
            if mapped:
                rows.append(mapped)
    return rows


def load_digimon(path: Path) -> list[dict]:
    rows: list[dict] = []
    for _sheet, frame in iter_excel(path):
        for rec in frame.to_dict(orient="records"):
            mapped = row(
                source="digimoncard",
                game="digimon",
                set_name=rec.get("set_name") or rec.get("series"),
                number=rec.get("id"),
                name=rec.get("name"),
                rarity=rec.get("rarity"),
                card_type=rec.get("type"),
            )
            if mapped:
                rows.append(mapped)
    return rows


def load_apitcg(path: Path) -> list[dict]:
    sheet_game = {
        "one piece cards": "onepiece",
        "pokemon cards": "pokemon",
        "dragon ball fusion cards": "dbsfw",
        "digimon cards": "digimon",
        "union arena cards": "unionarena",
        "gundam cards": "gundam",
        "riftbound cards": "riftbound",
    }
    rows: list[dict] = []
    for sheet, frame in iter_excel(path, sheets=None):
        game = sheet_game.get(str(sheet).lower())
        if not game:
            continue
        for rec in frame.to_dict(orient="records"):
            number = rec.get("code") or rec.get("number") or rec.get("id")
            set_name = rec.get("set.name") or rec.get("set_name")
            set_code = rec.get("set.id")
            if game == "pokemon":
                mapped = row(
                    source="apitcg",
                    game="pokemon",
                    set_name=rec.get("set.name") or rec.get("set_name"),
                    number=rec.get("number") or rec.get("id"),
                    name=rec.get("name"),
                    rarity=rec.get("rarity"),
                    card_type=rec.get("supertype"),
                )
            else:
                mapped = row(
                    source="apitcg",
                    game=game,
                    set_name=set_name,
                    set_code=set_code,
                    number=number,
                    name=rec.get("name"),
                    rarity=rec.get("rarity"),
                    card_type=rec.get("type") or rec.get("cardType"),
                    image_url=rec.get("images.large") or rec.get("images.small"),
                )
            if mapped:
                rows.append(mapped)
    return rows


def load_cardtrader(path: Path) -> list[dict]:
    import pandas as pd

    sheets = pd.read_excel(path, sheet_name=["Games", "Expansions", "Cards"], dtype=object)
    expansions = {}
    for rec in sheets["Expansions"].to_dict(orient="records"):
        expansions[rec.get("id")] = rec
    # Dedicated dumps already cover these; CardTrader has no collector numbers
    # so it cannot match their identities and would only add duplicates.
    skip_games = {
        "mtg",
        "pokemon",
        "yugioh",
        "onepiece",
        "lorcana",
        "fleshblood",
        "dbs",
        "dbsfw",
        "digimon",
        "unionarena",
        "gundam",
        "riftbound",
    }
    rows: list[dict] = []
    for rec in sheets["Cards"].to_dict(orient="records"):
        game = game_code(rec.get("game"))
        if not game or game in skip_games:
            continue
        expansion = expansions.get(rec.get("expansion_id"), {})
        mapped = row(
            source="cardtrader",
            game=game,
            set_name=rec.get("expansion") or expansion.get("name"),
            set_code=expansion.get("code"),
            name=rec.get("name"),
            variant=rec.get("version"),
            image_url=rec.get("image_url"),
        )
        if mapped:
            rows.append(mapped)
    return rows


def load_sports() -> list[dict]:
    import pandas as pd

    rows: list[dict] = []
    cards_path = locate("sports_cards.xlsx")
    if cards_path is None:
        return rows
    frame = pd.read_excel(cards_path, dtype=object)
    for rec in frame.to_dict(orient="records"):
        mapped = row(
            source="sports_cards",
            game="sports",
            language=rec.get("language") or "en",
            set_name=rec.get("set_name"),
            set_code=rec.get("set_id") or rec.get("source_set_id"),
            number=rec.get("number") or rec.get("card_number"),
            name=rec.get("display_name") or rec.get("subject") or rec.get("subject_name"),
            variant=rec.get("parallel"),
        )
        if mapped:
            rows.append(mapped)
    return rows


LOADERS = (
    ("scryfall_cards.xlsx", load_scryfall),
    ("tcgdex_cards.xlsx", load_tcgdex),
    ("pikaqian_cards.xlsx", load_pikaqian),
    ("ygoprodeck_cards.xlsx", load_ygoprodeck),
    ("apitcg_catalog.xlsx", load_apitcg),
    ("digimoncard_cards.xlsx", load_digimon),
    ("optcgapi_cards.xlsx", load_optcgapi),
    ("onepiece_cards.xlsx", load_onepiece),
    ("pokemontcgio_cards.xlsx", load_pokemontcgio),
    ("pokewallet_cards.xlsx", load_pokewallet),
    ("cardtrader_catalog.xlsx", load_cardtrader),
)


def merge_into(store: dict[str, dict], incoming: list[dict]) -> tuple[int, int]:
    added = filled = 0
    for item in incoming:
        key = item["identity"]
        existing = store.get(key)
        if existing is None:
            store[key] = item
            added += 1
            continue
        if item["source_rank"] < existing["source_rank"]:
            for field in COLUMNS:
                if field in {"identity", "source", "source_rank"}:
                    continue
                if not item.get(field) and existing.get(field):
                    item[field] = existing[field]
            store[key] = item
            filled += 1
            continue
        changed = False
        for field in COLUMNS:
            if field in {"identity", "source", "source_rank", "game", "language"}:
                continue
            if not existing.get(field) and item.get(field):
                existing[field] = item[field]
                changed = True
        if changed:
            filled += 1
    return added, filled


def write_sqlite(store: dict[str, dict], path: Path, stats: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA)
    connection.executemany(
        f"INSERT INTO cards ({', '.join(COLUMNS)}) VALUES ({', '.join('?' for _ in COLUMNS)})",
        [tuple(item[col] for col in COLUMNS) for item in store.values()],
    )
    connection.executemany(
        "INSERT INTO compose_info (key, value) VALUES (?, ?)",
        list(stats.items()),
    )
    connection.commit()
    connection.execute("VACUUM")
    connection.close()


def write_csv(store: dict[str, dict], path: Path) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    export_cols = [col for col in COLUMNS if col != "source_rank"]
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=export_cols)
        writer.writeheader()
        for item in sorted(
            store.values(),
            key=lambda row: (row["game"], row["language"], row.get("set_name") or "", row.get("number") or "", row["name"]),
        ):
            writer.writerow({col: item.get(col) for col in export_cols})


def main() -> int:
    store: dict[str, dict] = {}
    per_source: Counter[str] = Counter()

    print("Loading dump workbooks...")
    for filename, loader in LOADERS:
        path = locate(filename)
        if path is None:
            print(f"  skip {filename} (not found)")
            continue
        print(f"  {filename} ({path.stat().st_size / 1e6:.1f} MB)...")
        incoming = loader(path)
        added, filled = merge_into(store, incoming)
        per_source[filename] = len(incoming)
        print(f"    {len(incoming):,} rows → +{added:,} new, {filled:,} merged")
        del incoming

    sports = load_sports()
    if sports:
        added, filled = merge_into(store, sports)
        per_source["sports_cards.xlsx"] = len(sports)
        print(f"  sports_cards.xlsx → +{added:,} new, {filled:,} merged")

    if not store:
        print("No rows loaded.")
        return 1

    games = Counter(item["game"] for item in store.values())
    print("\nUnique printings by game:")
    for game, count in games.most_common():
        print(f"  {game:16} {count:,}")
    print(f"  {'TOTAL':16} {len(store):,}")

    stats = {
        "cards": str(len(store)),
        "games": str(len(games)),
        "sources": ",".join(name for name, _loader in LOADERS if locate(name)),
    }
    sqlite_path = BUILD / "composed_catalog.sqlite"
    csv_path = EXPORTS / "composed_cards.csv.gz"
    print(f"\nWriting {sqlite_path} ...")
    write_sqlite(store, sqlite_path, stats)
    print(f"Writing {csv_path} ...")
    write_csv(store, csv_path)
    print("Done.")
    print(f"  {sqlite_path}  ({sqlite_path.stat().st_size / 1e6:.1f} MB)")
    print(f"  {csv_path}     ({csv_path.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
