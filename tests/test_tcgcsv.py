"""TCGCSV loader maps TCGplayer category dumps into SetRecord / CardRecord."""

from __future__ import annotations

import json
from pathlib import Path

from pokedb.config import TCGCSV_CATEGORIES, TCGCSV_GAMES
from pokedb.match import SetRegistry, merge_cards
from pokedb.sources import tcgcsv


def test_tcgcsv_category_map_covers_requested_games():
    expected = {
        "yugioh",
        "mtg",
        "onepiece",
        "lorcana",
        "weiss",
        "dbz",
        "dbs",
        "dbsfw",
        "fleshblood",
        "metazoo",
        "warhammer",
        "dicemasters",
    }
    assert expected <= set(TCGCSV_CATEGORIES)
    assert TCGCSV_GAMES[68] == "onepiece"
    assert TCGCSV_GAMES[2] == "yugioh"


def test_tcgcsv_fetch_resolves_category_ids():
    from apis.tcgcsv_fetch import main

    # Dry validation path: unknown category exits non-zero without network.
    assert main(["--category", "99999"]) == 1


def test_tcgcsv_loader_reads_game_directory(tmp_path: Path, monkeypatch):
    game_dir = tmp_path / "onepiece"
    game_dir.mkdir()
    (game_dir / "groups.json").write_text(
        json.dumps(
            [
                {
                    "groupId": 1001,
                    "name": "Romance Dawn",
                    "abbreviation": "OP01",
                    "publishedOn": "2022-12-02",
                }
            ]
        ),
        encoding="utf-8",
    )
    (game_dir / "products_1001.json").write_text(
        json.dumps(
            [
                {
                    "productId": 42,
                    "name": "Monkey.D.Luffy",
                    "imageUrl": "https://example.test/luffy.png",
                    "extendedData": [
                        {"name": "Number", "value": "OP01-001"},
                        {"name": "Rarity", "value": "L"},
                    ],
                },
                {
                    "productId": 43,
                    "name": "Sealed Box",
                    "isPresale": True,
                },
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(tcgcsv, "TCGCSV_RAW", tmp_path)
    data = tcgcsv.load()
    assert data is not None
    assert len(data.sets) == 1
    assert data.sets[0].game == "onepiece"
    assert data.sets[0].abbreviation == "OP01"
    assert len(data.cards) == 1
    assert data.cards[0].number == "OP01-001"
    assert data.cards[0].rarity == "L"

    registry = SetRegistry([tcgcsv.SOURCE])
    for set_record in data.sets:
        registry.add(set_record)
    registry.assign_uids()
    rows, orphans = merge_cards(data.cards, registry, [tcgcsv.SOURCE])
    assert orphans == []
    assert rows[0]["card_uid"].startswith("onepiece:en:")
    assert rows[0]["number"] == "OP01-001"
