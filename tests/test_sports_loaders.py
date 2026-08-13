"""Tests for the curated sports spine and TCDB / Beckett loaders."""

from __future__ import annotations

import json
from pathlib import Path

from pokedb.match import SetRegistry, merge_cards
from pokedb.sources import beckett, sports_database_xlsx, tcdb


def _merge(source_name: str, data) -> list[dict]:
    registry = SetRegistry([source_name])
    for set_record in data.sets:
        registry.add(set_record)
    registry.assign_uids()
    rows, orphans = merge_cards(data.cards, registry, [source_name])
    assert orphans == []
    return rows


def test_sports_database_xlsx_loads_beckham_and_michaels(tmp_path: Path, monkeypatch):
    import openpyxl

    sources = tmp_path / "sources"
    sources.mkdir()
    _write_spine(openpyxl, sources)

    monkeypatch.setattr(
        sports_database_xlsx,
        "find_source_file",
        lambda name: sources / name if (sources / name).exists() else None,
    )

    data = sports_database_xlsx.load()
    assert data is not None
    assert len(data.sets) == 2
    assert len(data.cards) == 4

    rows = _merge(sports_database_xlsx.SOURCE, data)
    by_uid = {row["card_uid"]: row for row in rows}

    halo = next(row for row in rows if row["parallel"] == "HALO REF")
    assert halo["subject_name"] == "SIR DAVID BECKHAM"
    assert halo["number"] == "38"

    ruby = next(row for row in rows if row["parallel"] == "RUBY REF")
    assert ruby["notations"] == "AUTO"
    assert ruby["serial_number"] == "09"
    assert ruby["print_run"] == 15
    assert "SSL-SM" in ruby["card_uid"]
    assert by_uid  # non-empty

def test_tcdb_loader_maps_player_and_notations(tmp_path: Path, monkeypatch):
    raw = tmp_path / "tcdb"
    raw.mkdir()
    (raw / "football.json").write_text(
        json.dumps(
            {
                "sets": [
                    {
                        "id": "2024-topps-chrome-football",
                        "name": "2024 TOPPS CHROME FOOTBALL",
                        "manufacturer": "Topps",
                        "sport": "football",
                        "product_year": "2024",
                    }
                ],
                "cards": [
                    {
                        "set_id": "2024-topps-chrome-football",
                        "number": "1",
                        "player": "PATRICK MAHOMES",
                        "notations": "RC",
                        "parallel": "REFRACTOR",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tcdb, "TCDB_RAW", raw)

    data = tcdb.load()
    assert data is not None
    rows = _merge(tcdb.SOURCE, data)
    assert len(rows) == 1
    assert rows[0]["subject_name"] == "PATRICK MAHOMES"
    assert rows[0]["notations"] == "RC"
    assert rows[0]["parallel"] == "REFRACTOR"


def test_beckett_loader_maps_serial_parallel(tmp_path: Path, monkeypatch):
    raw = tmp_path / "beckett"
    raw.mkdir()
    (raw / "2024-panini-flawless-wwe.json").write_text(
        json.dumps(
            {
                "slug": "2024-panini-flawless-wwe",
                "set": {
                    "id": "2024-panini-flawless-wwe",
                    "name": "2024 PANINI FLAWLESS WWE",
                    "manufacturer": "Panini",
                    "sport": "wrestling",
                    "product_year": "2024",
                },
                "cards": [
                    {
                        "number": "SSL-SM",
                        "player": "SHAWN MICHAELS",
                        "notations": "AUTO",
                        "parallel": "RUBY REF",
                        "serial_number": "09",
                        "print_run": 15,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(beckett, "BECKETT_RAW", raw)

    data = beckett.load()
    assert data is not None
    rows = _merge(beckett.SOURCE, data)
    assert rows[0]["parallel"] == "RUBY REF"
    assert rows[0]["serial_number"] == "09"
    assert rows[0]["print_run"] == 15
    assert "SSL-SM" in rows[0]["card_uid"]


def test_tcdb_fetch_normalizes_dump():
    from apis.tcdb_fetch import normalize

    normalized = normalize(
        {
            "sets": [{"name": "2024 TOPPS SERIES 1", "manufacturer": "Topps", "year": "2024"}],
            "cards": [
                {
                    "set_id": "2024-topps-series-1",
                    "number": "50",
                    "subject": "SHOHEI OHTANI",
                    "notations": "SP",
                }
            ],
        }
    )
    assert len(normalized["sets"]) == 1
    assert normalized["sets"][0]["product_year"] == "2024"
    assert normalized["cards"][0]["player"] == "SHOHEI OHTANI"
    assert normalized["cards"][0]["notations"] == "SP"


def _write_spine(openpyxl, sources: Path) -> None:
    sets_book = openpyxl.Workbook()
    sets_sheet = sets_book.active
    sets_sheet.append(
        ["season", "manufacturer", "sport", "set_name", "release_date", "source_set_id", "language"]
    )
    sets_sheet.append(
        [
            "2025-26",
            "Topps",
            "soccer",
            "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
            "2025-09-01",
            "2025-26-topps-manchester-united-team-set",
            "en",
        ]
    )
    sets_sheet.append(
        [
            "2024",
            "Panini",
            "wrestling",
            "2024 PANINI FLAWLESS WWE",
            "2024-11-15",
            "2024-panini-flawless-wwe",
            "en",
        ]
    )
    sets_book.save(sources / "sports_database.xlsx")

    cards_book = openpyxl.Workbook()
    cards_sheet = cards_book.active
    cards_sheet.append(
        [
            "set_id",
            "set_name",
            "number",
            "subject",
            "parallel",
            "variant_tags",
            "serial_number",
            "serial_total",
            "display_name",
        ]
    )
    for row in [
        [
            "2025-26-topps-manchester-united-team-set",
            "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
            "38",
            "SIR DAVID BECKHAM",
            "",
            "",
            "",
            "",
            "SIR DAVID BECKHAM",
        ],
        [
            "2025-26-topps-manchester-united-team-set",
            "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
            "38",
            "SIR DAVID BECKHAM",
            "HALO REF",
            "",
            "",
            "",
            "SIR DAVID BECKHAM - HALO REF.",
        ],
        [
            "2024-panini-flawless-wwe",
            "2024 PANINI FLAWLESS WWE",
            "SSL-SM",
            "SHAWN MICHAELS",
            "",
            "",
            "",
            "",
            "SHAWN MICHAELS",
        ],
        [
            "2024-panini-flawless-wwe",
            "2024 PANINI FLAWLESS WWE",
            "SSL-SM",
            "SHAWN MICHAELS",
            "RUBY REF",
            "AUTO",
            "09",
            "15",
            "SHAWN MICHAELS – AUTO - RUBY REF. – 09/15",
        ],
    ]:
        cards_sheet.append(row)
    cards_book.save(sources / "sports_cards.xlsx")
