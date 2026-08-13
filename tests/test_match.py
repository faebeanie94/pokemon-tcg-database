from pokedb.match import SetRegistry, merge_cards
from pokedb.records import CardRecord, SetRecord

SOURCES = ["database.xlsx", "tcgdex"]


def make_registry() -> SetRegistry:
    return SetRegistry(list(SOURCES))


def curated(**kwargs) -> SetRecord:
    return SetRecord(source="database.xlsx", language="en", **kwargs)


def api(**kwargs) -> SetRecord:
    return SetRecord(source="tcgdex", language="en", **kwargs)


def test_sets_are_linked_by_folded_code():
    registry = make_registry()
    registry.add(curated(name="Base Set", abbreviation="BS", release_date="1999-01-09"))
    registry.add(
        api(source_set_id="base1", abbreviation="BS", name="Base Set", release_date="1999-01-09")
    )

    assert len(registry.canonical) == 1
    assert registry.canonical[0].matched_by["tcgdex"] == "code"


def test_code_reused_in_another_era_does_not_merge():
    """G1 is Gym Heroes in database.xlsx and Generations in TCGdex."""
    registry = make_registry()
    registry.add(curated(name="Gym Heroes", abbreviation="G1", release_date="2000-08-14"))
    registry.add(
        api(source_set_id="g1", abbreviation="G1", name="Generations", release_date="2016-02-22")
    )

    assert len(registry.canonical) == 2
    assert any("rejected on release year" in note for note in registry.notes)


def test_one_source_contributes_at_most_one_row_per_set():
    """Base Set and Base Set (Shadowless) share the code BS but are distinct."""
    registry = make_registry()
    registry.add(curated(name="Base Set", abbreviation="BS", release_date="1999-01-09"))
    registry.add(
        curated(name="Base Set (Shadowless)", abbreviation="BS", release_date="1999-01-09")
    )

    assert len(registry.canonical) == 2


def test_sets_are_linked_by_name_when_no_code_matches():
    registry = make_registry()
    registry.add(curated(name="Pokémon Jungle", release_date="1999-06-16"))
    registry.add(api(source_set_id="base2", name="Pokemon Jungle", release_date="1999-06-16"))

    assert len(registry.canonical) == 1
    assert registry.canonical[0].matched_by["tcgdex"] == "name"


def test_translated_names_are_linked_by_a_unique_release_date():
    """The Japanese sheet holds English translations, which share no characters."""
    registry = SetRegistry(list(SOURCES))
    registry.add(
        SetRecord(
            source="database.xlsx",
            language="ja",
            name_en="Expansion Pack",
            release_date="1996-10-20",
        )
    )
    registry.add(
        SetRecord(
            source="tcgdex",
            language="ja",
            source_set_id="PMCG1",
            name="拡張パック",
            release_date="1996-10-20",
        )
    )

    assert registry.link_by_unique_release_date() == 1
    registry.assign_uids()
    canonical = registry.canonical[0]
    assert canonical.first(SOURCES, "name") == "拡張パック"
    assert canonical.first(SOURCES, "name_en") == "Expansion Pack"


def test_a_shared_release_date_with_three_sets_is_left_alone():
    registry = SetRegistry(list(SOURCES))
    for index in range(2):
        registry.add(
            SetRecord(
                source="database.xlsx",
                language="ja",
                name_en=f"Deck {index}",
                release_date="2005-05-05",
            )
        )
    registry.add(
        SetRecord(
            source="tcgdex", language="ja", source_set_id="x", name="謎", release_date="2005-05-05"
        )
    )

    assert registry.link_by_unique_release_date() == 0


def test_set_identifiers_are_disambiguated_by_year():
    registry = make_registry()
    registry.add(curated(name="Sword & Shield Promos", abbreviation="SSP", release_date="2019-11-15"))
    registry.add(curated(name="Surging Sparks", abbreviation="SSP", release_date="2024-11-08"))
    registry.assign_uids()

    assert {item.set_uid for item in registry.canonical} == {
        "pokemon:en:ssp",
        "pokemon:en:ssp-2024",
    }


def test_same_code_in_different_games_does_not_merge():
    registry = make_registry()
    registry.add(curated(name="Base Set", abbreviation="BS", release_date="1999-01-09"))
    registry.add(
        SetRecord(
            source="tcgdex",
            game="mtg",
            language="en",
            source_set_id="bs",
            abbreviation="BS",
            name="Battlebond",
            release_date="2018-06-08",
        )
    )
    registry.assign_uids()
    assert len(registry.canonical) == 2
    uids = {item.set_uid for item in registry.canonical}
    assert "pokemon:en:bs" in uids
    assert "mtg:en:bs" in uids


def test_parallel_cards_get_distinct_uids():
    from pokedb.match import make_card_uid

    base = make_card_uid("sports:en:set", "38", None)
    parallel = make_card_uid("sports:en:set", "38", "HALO REF")
    assert base == "sports:en:set#38"
    assert parallel == "sports:en:set#38#haloref"
    assert base != parallel


def test_cards_from_two_sources_merge_into_one_row():
    registry = SetRegistry(list(SOURCES))
    registry.add(
        SetRecord(
            source="database.xlsx", language="en", source_set_id="SVI", abbreviation="SVI",
            name="Scarlet & Violet", release_date="2023-03-31",
        )
    )
    registry.add(
        api(source_set_id="svi", abbreviation="SVI", name="Scarlet & Violet",
            release_date="2023-03-31")
    )
    registry.assign_uids()

    rows, orphans = merge_cards(
        [
            CardRecord(
                source="tcgdex", language="en", source_set_id="svi", number="004",
                name="Sprigatito", image_url="https://example.test/4",
            ),
            CardRecord(
                source="database.xlsx", language="en", source_set_id="SVI", number="4",
                name="Sprigatito", name_en="Sprigatito",
            ),
        ],
        registry,
        SOURCES,
    )

    assert orphans == []
    assert len(rows) == 1
    # The higher precedence source sets the printed number, the other fills gaps.
    assert rows[0]["number"] == "4"
    assert rows[0]["image_url"] == "https://example.test/4"
    assert set(rows[0]["sources"].split(",")) == {"database.xlsx", "tcgdex"}


def test_cards_for_an_unknown_set_are_reported_not_dropped_silently():
    registry = make_registry()
    registry.assign_uids()
    rows, orphans = merge_cards(
        [CardRecord(source="tcgdex", language="en", source_set_id="nope", number="1", name="X")],
        registry,
        SOURCES,
    )

    assert rows == []
    assert len(orphans) == 1


def test_language_table_includes_scryfall_codes_and_undetermined():
    from pokedb.config import LANGUAGE_CODES

    assert "zhs" in LANGUAGE_CODES
    assert "zht" in LANGUAGE_CODES
    assert "und" in LANGUAGE_CODES
    assert "en" in LANGUAGE_CODES
