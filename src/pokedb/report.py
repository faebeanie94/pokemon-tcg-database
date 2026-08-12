"""Coverage and reconciliation reporting."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import DB_PATH, EXPORTS

COVERAGE = """
SELECT language_name, language, sets, sets_with_cards, cards, first_release, latest_release
FROM coverage_by_language
ORDER BY cards DESC, sets DESC
"""

SETS_WITHOUT_CARDS = """
SELECT l.name_en, COUNT(*)
FROM sets s JOIN languages l ON l.code = s.language
WHERE s.card_count_loaded = 0
GROUP BY l.name_en
ORDER BY COUNT(*) DESC
"""

DATE_CONFLICTS = """
SELECT s.language, COALESCE(s.name_en, s.name), s.abbreviation,
       GROUP_CONCAT(ss.source || '=' || ss.release_date, '  ')
FROM sets s
JOIN set_sources ss ON ss.set_uid = s.set_uid
WHERE ss.release_date IS NOT NULL
GROUP BY s.set_uid
HAVING COUNT(DISTINCT ss.release_date) > 1
ORDER BY s.language, s.release_date
"""

SOURCE_MIX = """
SELECT sources, COUNT(*) FROM sets GROUP BY sources ORDER BY COUNT(*) DESC
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(f"{db_path} not found - run `python -m pokedb build` first")
    return sqlite3.connect(db_path)


def print_report(db_path: Path = DB_PATH) -> None:
    connection = _connect(db_path)
    print("\nCoverage by language")
    print(f"  {'Language':<22}{'Sets':>7}{'With cards':>12}{'Cards':>9}  {'Released'}")
    for name, code, sets, with_cards, cards, first, last in connection.execute(COVERAGE):
        span = f"{(first or '?')[:4]}-{(last or '?')[:4]}"
        print(f"  {name:<22}{sets:>7}{with_cards:>12}{cards:>9}  {span}")

    totals = connection.execute(
        "SELECT COUNT(*), (SELECT COUNT(*) FROM cards) FROM sets"
    ).fetchone()
    print(f"  {'TOTAL':<22}{totals[0]:>7}{'':>12}{totals[1]:>9}")

    print("\nSets per source combination")
    for sources, count in connection.execute(SOURCE_MIX):
        print(f"  {count:>5}  {sources}")

    conflicts = connection.execute(DATE_CONFLICTS).fetchall()
    print(f"\nRelease dates that disagree between sources: {len(conflicts)}")
    for language, name, abbreviation, detail in conflicts[:10]:
        print(f"  {language:<6} {str(name)[:34]:<34} {str(abbreviation or ''):<10} {detail}")
    if len(conflicts) > 10:
        print(f"  ... and {len(conflicts) - 10} more (see exports/reconciliation.csv)")

    _write_reconciliation(connection, conflicts)
    connection.close()


def _write_reconciliation(connection: sqlite3.Connection, conflicts: list[tuple]) -> None:
    import csv

    EXPORTS.mkdir(parents=True, exist_ok=True)
    path = EXPORTS / "reconciliation.csv"
    missing = connection.execute(
        """
        SELECT s.language, COALESCE(s.name_en, s.name), s.abbreviation, s.release_date, s.sources
        FROM sets s
        WHERE s.card_count_loaded = 0
        ORDER BY s.language, COALESCE(s.release_date, '9999')
        """
    ).fetchall()

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["issue", "language", "set", "abbreviation", "detail", "sources"])
        for language, name, abbreviation, date, sources in missing:
            writer.writerow(["no card list", language, name, abbreviation, date or "", sources])
        for language, name, abbreviation, detail in conflicts:
            writer.writerow(["release date conflict", language, name, abbreviation, detail, ""])
    print(f"\nWrote {path}")
