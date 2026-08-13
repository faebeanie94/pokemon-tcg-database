"""Bandai JP One Piece dump staging + loader."""

from __future__ import annotations

import json
from pathlib import Path

from pokedb.fetch_bandai_onepiece import normalize
from pokedb.match import SetRegistry, merge_cards
from pokedb.sources import bandai_onepiece


def test_bandai_normalize_and_load(tmp_path: Path, monkeypatch):
    payload = {
        "sets": [{"id": "OP01", "name": "ROMANCE DAWN", "name_en": "ROMANCE DAWN", "language": "ja"}],
        "cards": [
            {
                "set_id": "OP01",
                "number": "001",
                "name": "モンキー・D・ルフィ",
                "name_en": "Monkey.D.Luffy",
                "language": "ja",
            }
        ],
    }
    sets, cards = normalize(payload)
    monkeypatch.setattr(bandai_onepiece, "RAW", tmp_path)
    (tmp_path / "sets.json").write_text(json.dumps(sets, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "cards.json").write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")

    data = bandai_onepiece.load()
    assert data is not None
    assert data.name == "bandai_onepiece"
    assert len(data.sets) == 1
    assert data.sets[0].language == "ja"
    assert data.cards[0].name == "モンキー・D・ルフィ"

    registry = SetRegistry(["bandai_onepiece"])
    for set_record in data.sets:
        registry.add(set_record)
    registry.assign_uids()
    rows, orphans = merge_cards(data.cards, registry, ["bandai_onepiece"])
    assert orphans == []
    assert rows[0]["card_uid"] == "onepiece:ja:op01#001"
