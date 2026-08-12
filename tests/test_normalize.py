import pytest

from pokedb.normalize import (
    clean_text,
    normalize_code,
    normalize_name,
    parse_date,
    split_number,
)


@pytest.mark.parametrize(
    "number, expected",
    [
        ("001", (None, 1)),
        ("4", (None, 4)),
        ("TG12", ("TG", 12)),
        ("SWSH284", ("SWSH", 284)),
        ("H1", ("H", 1)),
        ("", (None, None)),
        ("???", (None, None)),
    ],
)
def test_split_number(number, expected):
    assert split_number(number) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2023-03-31", "2023-03-31"),
        ("31/03/2023", "2023-03-31"),
        ("2023", "2023"),
        ("2023-03", "2023-03"),
        ("not a date", None),
        (None, None),
    ],
)
def test_parse_date(value, expected):
    assert parse_date(value) == expected


def test_clean_text_treats_spreadsheet_blanks_as_missing():
    assert clean_text(float("nan")) is None
    assert clean_text("  ") is None
    assert clean_text("NaN") is None
    assert clean_text(" Base Set ") == "Base Set"


def test_normalize_code_folds_case_and_punctuation():
    assert normalize_code("CS1.5C") == normalize_code("cs1.5c") == "cs15c"
    assert normalize_code("SV1S") == "sv1s"


def test_normalize_name_ignores_accents_and_punctuation():
    assert normalize_name("Pokémon Jungle") == normalize_name("pokemon jungle")
    assert normalize_name("Scarlet & Violet") == "scarletviolet"
