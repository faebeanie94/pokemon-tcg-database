import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pokedb.build import SCHEMA  # noqa: E402


@pytest.fixture
def sample_db(tmp_path: Path) -> Path:
    """A tiny database with two languages, so tests need no network."""
    path = tmp_path / "sample.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA.read_text(encoding="utf-8"))
    connection.executemany(
        "INSERT INTO languages (code, name_en, name_native, region) VALUES (?, ?, ?, ?)",
        [("en", "English", "English", "western"), ("ja", "Japanese", "日本語", "asian")],
    )
    connection.executemany(
        """
        INSERT INTO sets (set_uid, language, name, name_en, abbreviation, release_date,
                          release_year, card_count_official, sources, source_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'test', 1)
        """,
        [
            ("en:svi", "en", "Scarlet & Violet", "Scarlet & Violet", "SVI",
             "2023-03-31", 2023, 198),
            ("ja:sv1s", "ja", "スカーレットex", "Scarlet ex", "SV1S", "2023-01-20", 2023, 78),
        ],
    )
    connection.executemany(
        """
        INSERT INTO cards (card_uid, set_uid, language, number, number_prefix, number_value,
                           name, name_en, name_en_source, sources)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'test')
        """,
        [
            ("en:svi#004", "en:svi", "en", "004", None, 4, "Sprigatito", None, None),
            ("en:svi#TG12", "en:svi", "en", "TG12", "TG", 12, "Pikachu", None, None),
            ("ja:sv1s#001", "ja:sv1s", "ja", "001", None, 1, "リザードン", "Charizard", "pokeapi"),
        ],
    )
    connection.commit()
    connection.close()
    return path


@pytest.fixture
def client(sample_db: Path, monkeypatch):
    from fastapi.testclient import TestClient

    from pokedb import api

    monkeypatch.setenv("POKEDB_REFRESH_HOURS", "0")
    api.database.path = sample_db
    with TestClient(api.app) as test_client:
        yield test_client
