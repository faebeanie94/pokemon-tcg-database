# Multi-game data sources

Which categories can be loaded automatically, and which need curation.
`card_uid` cutover is in [MIGRATION.md](MIGRATION.md); sports checklists in
[SPORTS.md](SPORTS.md).

## Refresh policy

| Script | What it fetches | When to use |
| --- | --- | --- |
| `pnpm refresh` | **TCGdex only** (Pokémon), then build + match index | Daily Pokémon refresh — stays fast |
| `pnpm refresh:games` | TCGdex + TCGCSV + YGOPRODeck + Lorcast + GoAgain + apitcg | Multi-game without Scryfall’s huge dump |
| `pnpm fetch:mtg` | Scryfall bulk only | Magic; run `pokedb build && pnpm build:index` after |
| `pnpm fetch:onepiece` | TCGCSV + apitcg for One Piece | English One Piece; no Bandai JP scrape |

Scryfall `all_cards` is hundreds of MB and is **opt-in**, never part of
`pnpm refresh` / `refresh:games`. Prefer fetching only the games you grade:

```bash
PYTHONPATH=src python3 -m pokedb fetch --source tcgcsv --game onepiece --game lorcana
PYTHONPATH=src python3 -m pokedb build
pnpm build:index
```

`python -m pokedb update --source scryfall` also works: TCGdex always runs on
`update`, then any extra `--source` values.

## Automated (API / bulk dump)

| Category | Source | Notes |
| --- | --- | --- |
| Pokémon (all languages) | TCGdex + PikaQian + database.xlsx | Default `pnpm refresh` path |
| Magic: The Gathering (all languages) | Scryfall bulk `All Cards` | Opt-in via `pnpm fetch:mtg` |
| Yu-Gi-Oh! | TCGCSV (cat 2) + YGOPRODeck | YGOPRODeck: en/fr/de/it/pt only; no Japanese OCG text |
| One Piece | TCGCSV (cat 68) + apitcg | English-first; Bandai JP cardlist scrape is **deferred** |
| Lorcana | TCGCSV (cat 71) + Lorcast | English-centric |
| Flesh and Blood | TCGCSV (cat 62) + GoAgain / fab-cube | |
| Weiss Schwarz | TCGCSV (cat 20) | English releases only on TCGplayer |
| Dragon Ball Z (Panini TCG) | TCGCSV (cat 23) | |
| Dragon Ball Super: Masters | TCGCSV (cat 27) | |
| Dragon Ball Super: Fusion World | TCGCSV (cat 80) + apitcg | |
| MetaZoo | TCGCSV (cat 66) | Catalog is static (game discontinued) |
| Warhammer Age of Sigmar Champions | TCGCSV (cat 54) | Card game only — not miniatures |
| Marvel Dice Masters | TCGCSV (cat 18) | Dice + cards, not Marvel trading cards |

TCGCSV base: `https://tcgcsv.com/tcgplayer/` (no API key). Fetch with
`python3 apis/tcgcsv_fetch.py` or `PYTHONPATH=src python3 -m pokedb fetch --source tcgcsv`.
**Limitation:** English-market TCGplayer catalog only — not a multilingual source.

Spreadsheet exporters (optional, for offline / verify workflows):
`apis/tcgcsv_export.py`, `apis/scryfall_export.py`, `apis/ygoprodeck_export.py`.

## Sports & manufacturer lines (no catalog API)

Soccer, football, wrestling, UFC, Topps, Panini, Upper Deck, and Skybox checklists
are not published as structured APIs. Ingestion options:

1. **Curated spine** (default) — `sources/sports_database.xlsx` +
   `sources/sports_cards.xlsx`, plus `data/raw/sports/seed.json` /
   `sports_checklists.xlsx`.
2. **Normalized dumps** — `apis/tcdb_fetch.py` / `apis/beckett_fetch.py` write
   JSON under `data/raw/tcdb/` and `data/raw/beckett/` (no live scrape).
3. Commercial catalog vendors (e.g. CardSight).

See [SPORTS.md](SPORTS.md) for column layouts and merge precedence.

## Manual / community-only (Phase 5 backlog)

No catalog APIs; same curated JSON/xlsx approach when operators need them:

| Category | Strategy |
| --- | --- |
| Bandai Carddass | Community wiki / spreadsheet |
| Meiji promotional cards | Collector spreadsheets |
| Marvel trading cards (Fleer/Skybox/UD) | Sports-style curation (not Dice Masters) |
| UFC trading cards | Sports-style curation (seed has a Topps Chrome UFC sample) |
| Skybox | Manufacturer tag on sports sets (seed has 1996-97 Premium) |
| Bandai JP One Piece cardlist | Deferred; English via TCGCSV + apitcg |
| Warhammer (TCGPlayer cats 39–45) | Miniatures/paints/books — **not cards**; skip |

## Language coverage reality

| Claim | Reality |
| --- | --- |
| "All languages" for Magic | Scryfall (~19 languages) |
| "All languages" for Pokémon | TCGdex (16 languages in this repo) |
| "All languages" for Yu-Gi-Oh | YGOPRODeck: five Western languages only |
| Bandai games | English-first; Japanese via official sites (not automated here) |
| Sports cards | Typically English labels (`en`); `und` exists for language-neutral rows |

## Licensing

Bandai, Konami, Ravensburger, Wizards, Topps, and Panini assert rights over card
data and images. Community APIs often disclaim redistributing data rights. Fine
for an **internal grading tool**; do not republish catalogs without a license.
