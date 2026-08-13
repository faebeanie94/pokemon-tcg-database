"""Phase 4 language-rich loaders: Scryfall, YGOPRODeck, Lorcast, GoAgain, apitcg."""

from __future__ import annotations

import json
from pathlib import Path

from pokedb.sources import LOADERS, apitcg, goagain, lorcast, scryfall, ygoprodeck
from pokedb.sources import apitcg_onepiece, fab


def test_language_rich_loaders_precede_tcgcsv():
    names = [fn.__module__.rsplit(".", 1)[-1] for fn in LOADERS]
    assert names.index("scryfall") < names.index("tcgcsv")
    assert names.index("ygoprodeck") < names.index("tcgcsv")
    assert names.index("lorcast") < names.index("tcgcsv")
    assert names.index("goagain") < names.index("tcgcsv")
    assert names.index("apitcg") < names.index("tcgcsv")


def test_plan_aliases_reexport_loaders():
    assert fab.SOURCE == goagain.SOURCE
    assert fab.GAME == "fleshblood"
    assert fab.load is goagain.load
    assert apitcg_onepiece.SOURCE == apitcg.SOURCE
    assert apitcg_onepiece.GAME == "onepiece"
    assert apitcg_onepiece.load is apitcg.load


def test_scryfall_loader_reads_jsonl(tmp_path: Path, monkeypatch):
    raw = tmp_path / "scryfall"
    raw.mkdir()
    card = {
        "lang": "zhs",
        "set": "lea",
        "set_name": "Limited Edition Alpha",
        "collector_number": "1",
        "name": "Ancestral Recall",
        "printed_name": "祖先的回忆",
        "rarity": "rare",
        "type_line": "Instant",
        "id": "scry-1",
        "released_at": "1993-08-05",
        "image_uris": {"normal": "https://example.test/1.jpg"},
    }
    (raw / "all_cards.jsonl").write_text(json.dumps(card) + "\n", encoding="utf-8")
    monkeypatch.setattr(scryfall, "SCRYFALL_RAW", raw)

    data = scryfall.load()
    assert data is not None
    assert data.sets[0].game == "mtg"
    assert data.sets[0].language == "zhs"
    assert data.cards[0].name == "祖先的回忆"
    assert data.cards[0].name_en == "Ancestral Recall"


def test_ygoprodeck_loader_reads_language_dump(tmp_path: Path, monkeypatch):
    raw = tmp_path / "ygoprodeck"
    raw.mkdir()
    payload = {
        "data": [
            {
                "id": 46986414,
                "name": "Dark Magician",
                "type": "Normal Monster",
                "card_sets": [
                    {
                        "set_name": "Legend of Blue Eyes White Dragon",
                        "set_code": "LOB-EN005",
                        "set_rarity": "Ultra Rare",
                    }
                ],
                "card_images": [{"image_url": "https://example.test/dm.jpg"}],
            }
        ]
    }
    (raw / "en.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(ygoprodeck, "YGOPRODECK_RAW", raw)

    data = ygoprodeck.load()
    assert data is not None
    assert data.sets[0].game == "yugioh"
    assert data.cards[0].number == "LOB-EN005"
    assert data.cards[0].name == "Dark Magician"


def test_lorcast_loader_reads_sets_and_cards(tmp_path: Path, monkeypatch):
    raw = tmp_path / "lorcast"
    raw.mkdir()
    (raw / "sets.json").write_text(
        json.dumps([{"code": "TFC", "name": "The First Chapter", "released_at": "2023-08-18"}]),
        encoding="utf-8",
    )
    (raw / "cards_TFC.json").write_text(
        json.dumps(
            [
                {
                    "collector_number": "1",
                    "name": "Ariel - On Human Legs",
                    "rarity": "Common",
                    "type": "Character",
                    "id": "lor-1",
                    "image_uris": {"digital": {"large": "https://example.test/ariel.jpg"}},
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(lorcast, "LORCAST_RAW", raw)

    data = lorcast.load()
    assert data is not None
    assert data.sets[0].game == "lorcana"
    assert data.cards[0].name.startswith("Ariel")


def test_goagain_and_fab_alias(tmp_path: Path, monkeypatch):
    raw = tmp_path / "goagain"
    raw.mkdir()
    (raw / "sets.json").write_text(
        json.dumps([{"id": "WTR", "name": "Welcome to Rathe"}]),
        encoding="utf-8",
    )
    (raw / "cards.json").write_text(
        json.dumps(
            [{"set": "WTR", "number": "1", "name": "Dawnblade", "rarity": "Majestic", "id": "fab-1"}]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(goagain, "GOAGAIN_RAW", raw)

    data = fab.load()
    assert data is not None
    assert data.sets[0].game == "fleshblood"
    assert data.cards[0].name == "Dawnblade"


def test_apitcg_onepiece_alias(tmp_path: Path, monkeypatch):
    raw = tmp_path / "apitcg"
    (raw / "one-piece").mkdir(parents=True)
    (raw / "one-piece" / "sets.json").write_text(
        json.dumps([{"id": "OP01", "name": "Romance Dawn"}]),
        encoding="utf-8",
    )
    (raw / "one-piece" / "cards.json").write_text(
        json.dumps(
            [
                {
                    "set": "OP01",
                    "number": "001",
                    "name": "Luffy",
                    "rarity": "L",
                    "id": "op-1",
                    "image_url": "https://example.test/luffy.jpg",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(apitcg, "APITCG_RAW", raw)

    data = apitcg_onepiece.load()
    assert data is not None
    assert data.sets[0].game == "onepiece"
    assert data.cards[0].name == "Luffy"
