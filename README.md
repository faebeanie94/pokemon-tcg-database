# Pokemon TCG Card Database

Every official Pokemon Trading Card Game set and card, in every language it has
been printed in, as **one Excel workbook** and a **JSON API**.

Built for card identification at grading intake: find a card from the set name,
the number printed on it, the card name and the year it was released.

| | |
|---|---|
| Workbook | [`exports/Pokemon_TCG_Card_Database.xlsx`](exports/Pokemon_TCG_Card_Database.xlsx) |
| Coverage | 2,206 sets and 144,851 cards across 16 languages |
| Refresh | `python -m pokedb update`, a scheduled GitHub Action, or the API's own timer |

## The workbook

One file, four sheets:

- **Cards** - one row per card: Language, Set Name, Card Number, Card Name,
  Year, plus the English set/card name and set code.
- **Sets** - one row per set: name, code, release date, series and card counts.
- **Coverage** - how many sets and cards exist per language.
- **About** - when it was generated and from what.

Row 1 of every sheet has filter arrows: filter by Language, then Set Name (or
Set Code), then Card Number. `Cards In Set` is the printed set size, so any card
numbered above it is a secret rare.

The workbook is regenerated from scratch on every update, so corrections belong
in the source spreadsheets (below), not in the output file.

## The API

```bash
pip install -r requirements.txt
python -m pokedb update                 # download, build, export
uvicorn pokedb.api:app --host 0.0.0.0 --port 8000
```

Interactive documentation is served at `/docs`.

| Endpoint | Purpose |
|---|---|
| `GET /v1/lookup?set=SVI&number=004/198` | Identify a card from what is printed on it |
| `GET /v1/cards?q=Charizard&language=ja` | Search cards, in any language, by English or local name |
| `GET /v1/sets?language=en&year=2024` | List sets |
| `GET /v1/sets/{set_uid}/cards` | Every card in a set |
| `GET /v1/languages` | Languages and their coverage |
| `GET /v1/download/workbook` | Download the current Excel workbook |
| `GET /health` | Liveness plus when the data was last built |

`lookup` is the grading-intake endpoint: it accepts a set code (`SVI`), an
English set name (`Surging Sparks`) or a local one (`スカーレットex`), and a
number written as `4`, `004` or `004/198`. Exact set matches rank above partial
ones.

### Keeping it up to date

The service rebuilds itself on a timer - `POKEDB_REFRESH_HOURS` (default 24) -
by re-downloading the sources, building a new database file and swapping it in
atomically, so queries are never interrupted. Set it to `0` to disable, and
trigger a rebuild on demand with `POST /v1/admin/refresh` (bearer
`POKEDB_ADMIN_TOKEN`).

| Variable | Default | Meaning |
|---|---|---|
| `POKEDB_DB` | `build/pokemon_tcg.sqlite` | Database location |
| `POKEDB_REFRESH_HOURS` | `24` | Hours between automatic rebuilds, `0` to disable |
| `POKEDB_ADMIN_TOKEN` | unset | Token for `POST /v1/admin/refresh` |
| `POKEDB_CORS_ORIGINS` | `*` | Comma separated allowed origins |

## Where the data comes from

| Source | Contributes |
|---|---|
| [TCGdex](https://tcgdex.dev) API | Card lists for 16 languages, set codes and release dates |
| `database.xlsx` | Hand-curated master set list (English, Japanese, Simplified Chinese) with abbreviations and release dates |
| `pikaqian_cards.xlsx` | Simplified Chinese cards - 12,323 of them, against 877 in the API |
| [PokeAPI](https://pokeapi.co) species names | English names for cards printed in Japanese, Chinese, Korean and the European languages |
| `tcgdex_cards.xlsx` | Not imported; `python -m pokedb verify` checks it against the API to catch cards the API has dropped |

The same set is described differently by each source, so sets are linked by
folded set code first (`CSM1cC` = `csm1cc`), then by name, then by a unique
release date. A release-year guard stops codes that were reused across eras
from merging - `G1` is Gym Heroes in `database.xlsx` and Generations in TCGdex.
Where sources disagree on a release date, `database.xlsx` wins; every
disagreement is listed in `exports/reconciliation.csv`.

English names for Japanese, Chinese and Korean cards are derived from the
species name (リザードンex becomes "Charizard ex") and marked `pokeapi` in the
`name_en_source` column. Names with an owner prefix are left untranslated
rather than risk a wrong name on a label.

## Commands

```bash
python -m pokedb update    # fetch, build, export, report - the usual refresh
python -m pokedb fetch     # download the latest data only
python -m pokedb build     # merge the sources into build/pokemon_tcg.sqlite
python -m pokedb export    # write the workbook and CSVs
python -m pokedb report    # coverage and source disagreements
python -m pokedb verify    # check tcgdex_cards.xlsx against the API
```

Also written: `exports/sets.csv`, `exports/cards.csv.gz` (for loading into
another system) and `exports/reconciliation.csv` (sets with no card list, and
release dates the sources disagree on).

## Adding or correcting data

Add a sheet or rows to `database.xlsx` - one sheet per language, named after it
("English Sets", "Korean Sets"), with columns `#`, `Set Name`, `Abbreviation`,
`Release Date` and `Series`. Anything you add is merged into the next build and
takes precedence over the API, which is how you correct a wrong release date or
add a set the public sources do not carry.

## Coverage

Card lists are complete for English and the main European languages, and thin
for Japanese, Korean, Thai and Indonesian, where the public sources only carry
part of the catalogue. `python -m pokedb report` prints the current state and
`exports/reconciliation.csv` lists every set that has no card list yet.
