"""Read-only JSON API over the built database.

Run it with::

    uvicorn pokedb.api:app --host 0.0.0.0 --port 8000

The service opens the SQLite file read-only, so it can be scaled out behind a
load balancer. When ``POKEDB_REFRESH_HOURS`` is set the process rebuilds the
database on that interval in a background thread and swaps the file in
atomically, which is how the data keeps itself up to date without a deploy.

Environment variables
    POKEDB_DB              path to the SQLite file (default build/pokemon_tcg.sqlite)
    POKEDB_REFRESH_HOURS   hours between automatic rebuilds; 0 disables (default 24)
    POKEDB_ADMIN_TOKEN     bearer token required by POST /v1/admin/refresh
    POKEDB_CORS_ORIGINS    comma separated allowed origins (default *)
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Iterable

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import DB_PATH, EXPORTS
from .normalize import normalize_code, split_number

MAX_PAGE_SIZE = 500

CARD_COLUMNS = """
    c.card_uid, c.set_uid, c.language, s.name AS set_name, s.name_en AS set_name_en,
    s.abbreviation AS set_code, s.release_date, s.release_year AS year,
    c.number AS card_number, c.name AS card_name, c.name_en AS card_name_en,
    c.rarity, s.card_count_official AS cards_in_set, c.image_url, c.sources
"""

SET_COLUMNS = """
    s.set_uid, s.language, s.name, s.name_en, s.abbreviation AS code,
    s.release_date, s.release_year AS year, s.series_name AS series,
    s.card_count_official AS cards_in_set, s.card_count_loaded AS cards_listed, s.sources
"""


class Database:
    """Holds the path to the active SQLite file and hands out connections."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def connect(self) -> sqlite3.Connection:
        if not self.path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"database not built yet ({self.path}); run `python -m pokedb update`",
            )
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        connection = self.connect()
        try:
            return [dict(row) for row in connection.execute(sql, tuple(params))]
        finally:
            connection.close()

    def scalar(self, sql: str, params: Iterable[Any] = ()) -> Any:
        connection = self.connect()
        try:
            row = connection.execute(sql, tuple(params)).fetchone()
            return row[0] if row else None
        finally:
            connection.close()

    def refresh(self) -> dict[str, Any]:
        """Re-download, rebuild and swap in a new database file."""
        if not self._lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="a refresh is already running")
        try:
            from .build import build
            from .export import export_all
            from .fetch_tcgdex import fetch_all

            fetch_all()
            staging = self.path.with_suffix(".staging.sqlite")
            stats = build(db_path=staging)
            os.replace(staging, self.path)
            export_all()
            return stats
        finally:
            self._lock.release()


database = Database(Path(os.environ.get("POKEDB_DB", DB_PATH)))


def _refresh_loop(interval_hours: float, stop: threading.Event) -> None:
    while not stop.wait(interval_hours * 3600):
        try:
            database.refresh()
        except Exception as error:  # noqa: BLE001 - a failed refresh must not kill the service
            print(f"scheduled refresh failed: {error}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    interval = float(os.environ.get("POKEDB_REFRESH_HOURS", "24"))
    stop = threading.Event()
    worker = None
    if interval > 0:
        worker = threading.Thread(
            target=_refresh_loop, args=(interval, stop), name="pokedb-refresh", daemon=True
        )
        worker.start()
    yield
    stop.set()
    if worker:
        worker.join(timeout=1)


app = FastAPI(
    title="Pokemon TCG Card Database",
    version="1.0.0",
    summary="Every official Pokemon TCG set and card, in every language it was printed in.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get("POKEDB_CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def require_admin(authorization: str = Header(default="")) -> None:
    token = os.environ.get("POKEDB_ADMIN_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="POKEDB_ADMIN_TOKEN is not configured")
    if authorization.removeprefix("Bearer ").strip() != token:
        raise HTTPException(status_code=401, detail="invalid admin token")


def _paginate(sql: str, params: list[Any], page: int, page_size: int) -> dict[str, Any]:
    total = database.scalar(f"SELECT COUNT(*) FROM ({sql})", params)
    rows = database.query(
        f"{sql} LIMIT ? OFFSET ?", [*params, page_size, (page - 1) * page_size]
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "items": rows,
    }


@app.get("/health", tags=["service"])
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "database": str(database.path),
        "built_at": database.scalar("SELECT value FROM build_info WHERE key = 'built_at'"),
        "sets": database.scalar("SELECT COUNT(*) FROM sets"),
        "cards": database.scalar("SELECT COUNT(*) FROM cards"),
    }


@app.get("/v1/languages", tags=["reference"])
def languages() -> list[dict]:
    return database.query(
        """
        SELECT language AS code, language_name AS name, sets, sets_with_cards, cards,
               first_release, latest_release
        FROM coverage_by_language
        ORDER BY cards DESC, sets DESC
        """
    )


@app.get("/v1/sets", tags=["sets"])
def list_sets(
    language: str | None = Query(default=None, description="language code, e.g. 'en'"),
    q: str | None = Query(default=None, description="search set name (any language)"),
    code: str | None = Query(default=None, description="exact set code, e.g. 'SVI'"),
    year: int | None = None,
    series: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=MAX_PAGE_SIZE),
) -> dict[str, Any]:
    where, params = ["1 = 1"], []
    if language:
        where.append("s.language = ?")
        params.append(language)
    if code:
        where.append("REPLACE(LOWER(s.abbreviation), '.', '') = ?")
        params.append(normalize_code(code) or code.lower())
    if year:
        where.append("s.release_year = ?")
        params.append(year)
    if series:
        where.append("s.series_name LIKE ?")
        params.append(f"%{series}%")
    if q:
        where.append("(s.name LIKE ? OR s.name_en LIKE ? OR s.abbreviation LIKE ?)")
        params.extend([f"%{q}%"] * 3)

    sql = (
        f"SELECT {SET_COLUMNS} FROM sets s WHERE {' AND '.join(where)} "
        "ORDER BY COALESCE(s.release_date, '9999'), s.language, s.name"
    )
    return _paginate(sql, params, page, page_size)


@app.get("/v1/sets/{set_uid}", tags=["sets"])
def get_set(set_uid: str) -> dict:
    rows = database.query(f"SELECT {SET_COLUMNS} FROM sets s WHERE s.set_uid = ?", [set_uid])
    if not rows:
        raise HTTPException(status_code=404, detail="set not found")
    result = rows[0]
    result["sources_detail"] = database.query(
        "SELECT source, source_set_id, name, name_en, abbreviation, release_date, matched_by "
        "FROM set_sources WHERE set_uid = ?",
        [set_uid],
    )
    return result


@app.get("/v1/sets/{set_uid}/cards", tags=["cards"])
def set_cards(
    set_uid: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=500, ge=1, le=MAX_PAGE_SIZE),
) -> dict[str, Any]:
    sql = (
        f"SELECT {CARD_COLUMNS} FROM cards c JOIN sets s ON s.set_uid = c.set_uid "
        "WHERE c.set_uid = ? "
        "ORDER BY COALESCE(c.number_prefix, ''), COALESCE(c.number_value, 999999), c.number"
    )
    return _paginate(sql, [set_uid], page, page_size)


@app.get("/v1/cards", tags=["cards"])
def list_cards(
    q: str | None = Query(default=None, description="search card name (any language)"),
    language: str | None = None,
    set_uid: str | None = None,
    set_code: str | None = Query(default=None, description="set code, e.g. 'SVI'"),
    number: str | None = Query(default=None, description="card number as printed"),
    year: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=MAX_PAGE_SIZE),
) -> dict[str, Any]:
    where, params = ["1 = 1"], []
    if language:
        where.append("c.language = ?")
        params.append(language)
    if set_uid:
        where.append("c.set_uid = ?")
        params.append(set_uid)
    if set_code:
        where.append("REPLACE(LOWER(s.abbreviation), '.', '') = ?")
        params.append(normalize_code(set_code) or set_code.lower())
    if year:
        where.append("s.release_year = ?")
        params.append(year)
    if q:
        where.append("(c.name LIKE ? OR c.name_en LIKE ?)")
        params.extend([f"%{q}%"] * 2)
    if number:
        prefix, value = split_number(number)
        if value is not None:
            where.append(
                "(c.number = ? OR (COALESCE(c.number_prefix,'') = ? AND c.number_value = ?))"
            )
            params.extend([number, prefix or "", value])
        else:
            where.append("c.number = ?")
            params.append(number)

    sql = (
        f"SELECT {CARD_COLUMNS} FROM cards c JOIN sets s ON s.set_uid = c.set_uid "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY COALESCE(s.release_date, '9999'), s.name, "
        "COALESCE(c.number_prefix, ''), COALESCE(c.number_value, 999999)"
    )
    return _paginate(sql, params, page, page_size)


@app.get("/v1/lookup", tags=["cards"])
def lookup(
    set: str = Query(description="set name, English name or set code"),  # noqa: A002
    number: str = Query(description="card number as printed, e.g. '004/165'  or 'TG12'"),
    language: str | None = Query(default=None, description="restrict to one language"),
) -> dict[str, Any]:
    """Identify a card from what is printed on it.

    Built for grading intake: pass the set as it appears on the label and the
    collector number (``4``, ``004`` and ``004/165`` are all accepted). Exact
    set-code and set-name matches are returned ahead of partial matches.
    """
    printed_number = number.split("/")[0].strip()
    prefix, value = split_number(printed_number)
    parameters: dict[str, Any] = {
        "folded": normalize_code(set) or set.lower(),
        "raw": set.strip().lower(),
        "like": f"%{set.strip()}%",
        "number": printed_number,
        "number_lower": printed_number.lower(),
        "prefix": prefix or "",
        "value": value,
    }

    where = []
    if language:
        where.append("c.language = :language")
        parameters["language"] = language
    if value is not None:
        where.append(
            "(c.number = :number "
            "OR (COALESCE(c.number_prefix,'') = :prefix AND c.number_value = :value))"
        )
    else:
        where.append("LOWER(c.number) = :number_lower")

    # Rank: exact code, exact name, then partial name.
    rank = """
        CASE
            WHEN REPLACE(LOWER(s.abbreviation), '.', '') = :folded THEN 0
            WHEN LOWER(s.name) = :raw OR LOWER(s.name_en) = :raw THEN 1
            WHEN s.name LIKE :like OR s.name_en LIKE :like THEN 2
            ELSE 3
        END
    """
    sql = (
        f"SELECT {CARD_COLUMNS}, {rank} AS match_rank "
        "FROM cards c JOIN sets s ON s.set_uid = c.set_uid "
        f"WHERE {' AND '.join(where)} "
        f"AND {rank} < 3 "
        "ORDER BY match_rank, COALESCE(s.release_date, '9999') "
        "LIMIT 50"
    )
    connection = database.connect()
    try:
        rows = [dict(row) for row in connection.execute(sql, parameters)]
    finally:
        connection.close()

    return {
        "query": {"set": set, "number": number, "language": language},
        "matches": len(rows),
        "items": rows,
    }


@app.get("/v1/stats", tags=["service"])
def stats() -> dict[str, Any]:
    return {
        "build": {
            row["key"]: row["value"] for row in database.query("SELECT key, value FROM build_info")
        },
        "languages": database.query(
            "SELECT language AS code, language_name AS name, sets, cards "
            "FROM coverage_by_language ORDER BY cards DESC"
        ),
    }


@app.get("/v1/download/workbook", tags=["service"])
def download_workbook() -> FileResponse:
    path = EXPORTS / "Pokemon_TCG_Card_Database.xlsx"
    if not path.exists():
        raise HTTPException(status_code=404, detail="workbook has not been exported yet")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


@app.post("/v1/admin/refresh", tags=["service"], dependencies=[Depends(require_admin)])
def refresh() -> dict[str, Any]:
    started = time.time()
    stats = database.refresh()
    return {"status": "ok", "seconds": round(time.time() - started, 1), **stats}
