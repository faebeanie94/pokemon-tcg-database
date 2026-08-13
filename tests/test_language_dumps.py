"""Language-gap dump staging (Weiss JP / YGO OCG / Lorcana i18n)."""

from __future__ import annotations

import json
from pathlib import Path

from pokedb.fetch_language_dumps import normalize, write_dump
from pokedb.sources import language_dumps


def test_weiss_jp_dump_loads(tmp_path: Path):
    payload = {
        "sets": [{"id": "WS01", "name": "ブースターパック", "name_en": "Booster Pack", "language": "ja"}],
        "cards": [
            {
                "set_id": "WS01",
                "number": "001",
                "name": "テストカード",
                "name_en": "Test Card",
                "language": "ja",
            }
        ],
    }
    sets, cards = normalize(payload, default_language="ja")
    dump_dir = tmp_path / "weiss_jp"
    dump_dir.mkdir()
    (dump_dir / "sets.json").write_text(json.dumps(sets, ensure_ascii=False), encoding="utf-8")
    (dump_dir / "cards.json").write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")

    data = language_dumps._load_one("weiss_jp", "weiss", dump_dir, "ja")
    assert data is not None
    assert data.cards[0].name == "テストカード"
    assert data.sets[0].game == "weiss"


def test_write_dump_targets(tmp_path: Path, monkeypatch):
    from pokedb import fetch_language_dumps as fld

    monkeypatch.setitem(fld.TARGETS, "weiss_jp", {**fld.TARGETS["weiss_jp"], "dir": tmp_path / "w"})
    sets, cards = normalize(
        {"sets": [{"id": "A", "name": "A"}], "cards": [{"set_id": "A", "number": "1", "name": "n"}]},
        default_language="ja",
    )
    out = write_dump("weiss_jp", sets, cards)
    assert (out / "sets.json").exists()
    assert (out / "cards.json").exists()
