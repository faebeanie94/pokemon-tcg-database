"""Derive English card names for cards printed in other languages.

TCGdex returns a Japanese card only under its Japanese name, which is no use to
an English-speaking grader. PokeAPI publishes every Pokemon species name in
every official language, so a card whose name starts with a species name can be
given an English equivalent: リザードンex -> "Charizard ex".

Only the species part is translated and only when it sits at the start of the
name. A card such as ロケット団のミュウツー ("Team Rocket's Mewtwo") is left
alone rather than being labelled a plain "Mewtwo", because a wrong name on a
grading label is worse than a missing one.
"""

from __future__ import annotations

import csv
import io

from .config import DATA_RAW

SPECIES_CSV = (
    "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/"
    "pokemon_species_names.csv"
)
CACHE = DATA_RAW / "pokeapi" / "pokemon_species_names.csv"
ENGLISH_LANGUAGE_ID = 9

# PokeAPI language id -> the language codes used in this database.
POKEAPI_LANGUAGES: dict[int, tuple[str, ...]] = {
    1: ("ja",),        # Japanese, kana - how most card names are printed
    3: ("ko",),
    4: ("zh-tw",),
    5: ("fr",),
    6: ("de",),
    7: ("es",),
    8: ("it",),
    11: ("ja",),       # Japanese, official spelling
    12: ("zh-cn",),
    13: ("pt-br", "pt"),
}


def _download() -> str:
    if CACHE.exists():
        return CACHE.read_text(encoding="utf-8")
    import requests

    response = requests.get(SPECIES_CSV, timeout=60)
    response.raise_for_status()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(response.text, encoding="utf-8")
    return response.text


class SpeciesTranslator:
    """Maps a localised species name to its English name, per language."""

    def __init__(self, rows: list[dict[str, str]]) -> None:
        english: dict[str, str] = {}
        localised: dict[str, dict[str, str]] = {}
        for row in rows:
            species_id = row["pokemon_species_id"]
            language_id = int(row["local_language_id"])
            name = row["name"].strip()
            if not name:
                continue
            if language_id == ENGLISH_LANGUAGE_ID:
                english[species_id] = name
                continue
            for code in POKEAPI_LANGUAGES.get(language_id, ()):
                localised.setdefault(code, {})[name] = species_id

        self.by_language: dict[str, dict[str, str]] = {}
        for code, names in localised.items():
            self.by_language[code] = {
                name: english[species_id]
                for name, species_id in names.items()
                if species_id in english
            }
        # Longest name first so ピカチュウ is preferred over ピカ- prefixes.
        self.ordered: dict[str, list[str]] = {
            code: sorted(names, key=len, reverse=True) for code, names in self.by_language.items()
        }

    def supports(self, language: str) -> bool:
        return language in self.by_language

    def english_name(self, language: str, card_name: str) -> str | None:
        names = self.by_language.get(language)
        if not names:
            return None
        exact = names.get(card_name)
        if exact:
            return exact
        for species in self.ordered[language]:
            if card_name.startswith(species):
                suffix = card_name[len(species) :].strip()
                return f"{names[species]} {suffix}".strip() if suffix else names[species]
        return None


def load_translator(offline_ok: bool = True) -> SpeciesTranslator | None:
    try:
        text = _download()
    except Exception as error:  # noqa: BLE001 - translation is a nice-to-have
        if not offline_ok:
            raise
        print(f"  ! species names unavailable ({error}); skipping English name derivation")
        return None
    return SpeciesTranslator(list(csv.DictReader(io.StringIO(text))))
