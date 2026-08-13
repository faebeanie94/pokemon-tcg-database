"""The tracked sports seed must include the two grading examples."""

from pokedb.match import SetRegistry, merge_cards
from pokedb.sources.sports_json import SOURCE, load


def _merged_seed_rows() -> list[dict]:
    data = load()
    assert data is not None, "data/raw/sports/seed.json is missing or empty"
    registry = SetRegistry([SOURCE])
    for set_record in data.sets:
        registry.add(set_record)
    registry.assign_uids()
    rows, orphans = merge_cards(data.cards, registry, [SOURCE])
    assert orphans == []
    return rows


def test_seed_loads_the_beckham_halo_ref_printing():
    rows = _merged_seed_rows()
    by_uid = {row["card_uid"]: row for row in rows}

    base = by_uid["sports:en:202526toppsmanchesterunitedteamset#38"]
    halo = by_uid["sports:en:202526toppsmanchesterunitedteamset#38#haloref"]

    assert base["subject_name"] == "SIR DAVID BECKHAM"
    assert base["parallel"] is None
    assert halo["subject_name"] == "SIR DAVID BECKHAM"
    assert halo["parallel"] == "HALO REF"
    assert halo["number"] == "38"


def test_seed_loads_the_michaels_ruby_serial():
    rows = _merged_seed_rows()
    by_uid = {row["card_uid"]: row for row in rows}

    base = by_uid["sports:en:2024paniniflawlesswwe#SSL-SM"]
    ruby = by_uid["sports:en:2024paniniflawlesswwe#SSL-SM#rubyref"]

    assert base["subject_name"] == "SHAWN MICHAELS"
    assert ruby["number"] == "SSL-SM"
    assert ruby["parallel"] == "RUBY REF"
    assert ruby["notations"] == "AUTO"
    assert ruby["serial_number"] == "09"
    assert ruby["print_run"] == 15
    # 09/15 is a print run, not a Pokémon-style printed total.
    assert ruby["number"] != "09"


def test_seed_covers_manufacturers_and_sports():
    data = load()
    assert data is not None
    manufacturers = {s.manufacturer for s in data.sets}
    sports = {s.sport for s in data.sets}
    assert {"Topps", "Panini", "Upper Deck", "Skybox"} <= manufacturers
    assert {"soccer", "football", "wrestling", "basketball", "ufc"} <= sports

    rows = _merged_seed_rows()
    assert len(rows) >= 20
    by_uid = {row["card_uid"]: row for row in rows}
    assert any("messi" in (row["subject_name"] or "").lower() for row in rows)
    assert any("jordan" in (row["subject_name"] or "").lower() for row in rows)
    assert any("mcgregor" in (row["subject_name"] or "").lower() for row in rows)
    # Skybox set is present as a manufacturer tag example.
    assert any(uid.startswith("sports:en:199697skyboxpremiumbasketball") for uid in by_uid)
