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
| `pnpm fetch:onepiece` | TCGCSV + apitcg for One Piece | English One Piece; JP via Bandai dump staging |

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
| Magic: The Gathering (all languages) | Scryfall bulk | Opt-in via `pnpm fetch:mtg` (defaults to `default_cards`; use `all_cards` for every language) |
| Yu-Gi-Oh! | TCGCSV (cat 2) + YGOPRODeck | YGOPRODeck: en/fr/de/it/pt only; no Japanese OCG text |
| One Piece | TCGCSV (cat 68) + apitcg + Bandai JP dumps | English-first; JP via `data/raw/bandai_onepiece/` |
| Lorcana | TCGCSV (cat 71) + Lorcast | English-centric |
| Flesh and Blood | TCGCSV (cat 62) + GoAgain / fab-cube | |
| Weiss Schwarz | TCGCSV (cat 20) | English releases only on TCGplayer |
| Dragon Ball Z (Panini TCG) | TCGCSV (cat 23) | |
| Dragon Ball Super: Masters | TCGCSV (cat 27) | |
| Dragon Ball Super: Fusion World | TCGCSV (cat 80) + apitcg | |
| MetaZoo | TCGCSV (cat 66) | Catalog is static (game discontinued) |
| Warhammer Age of Sigmar Champions | TCGCSV (cat 54) | Card game only — not miniatures |
| Marvel Dice Masters | TCGCSV (cat 18) | Dice + cards, not Marvel trading cards |
| UniVersus | TCGCSV (cat 25) | English TCGplayer catalog |
| Sports / entertainment | Curated xlsx + TCDB/Beckett dumps | No public Topps/Panini API |

TCGCSV base: `https://tcgcsv.com/tcgplayer/` (no API key). Fetch with
`python3 apis/tcgcsv_fetch.py` or `PYTHONPATH=src python3 -m pokedb fetch --source tcgcsv`.
**Limitation:** English-market TCGplayer catalog only — not a multilingual source.

Spreadsheet exporters (optional, for offline / verify workflows):
`apis/tcgcsv_export.py`, `apis/scryfall_export.py`, `apis/ygoprodeck_export.py`.

## Language-rich sources (Phase 4)

Dedicated fetchers beyond English-only TCGCSV. Loaders live under
`src/pokedb/sources/`; fetch with `PYTHONPATH=src python3 -m pokedb fetch --source …`.

| Game | Source / loader | Languages | Fetch |
| --- | --- | --- | --- |
| Magic | Scryfall (`scryfall.py`) | ~19 (incl. `zhs`/`zht`/`ja`) | `pnpm fetch:mtg` |
| Yu-Gi-Oh! | YGOPRODeck (`ygoprodeck.py`) | en/fr/de/it/pt only | `refresh:games` |
| One Piece | apitcg (`apitcg.py`, alias `apitcg_onepiece.py`) + TCGCSV + Bandai JP dumps | English via API (needs `APITCG_API_KEY`); JP via `data/raw/bandai_onepiece/` | `pnpm fetch:onepiece` |
| Lorcana | Lorcast (`lorcast.py`) + TCGCSV | primarily en | `refresh:games` |
| Flesh and Blood | GoAgain (`goagain.py`, alias `fab.py`) + TCGCSV | en | `refresh:games` |
| DBS Fusion World | apitcg + TCGCSV | en | `refresh:games` |
| Weiss Schwarz | TCGCSV only | en (JP Bushiroad sets **absent**) | TCGCSV |

Language-rich loaders are registered **before** TCGCSV in `LOADERS`, so Scryfall
beats TCGplayer English for Magic when both dumps are present.

### Japanese / other-language gaps (follow-up scrapes)

| Gap | Why | Follow-up |
| --- | --- | --- |
| Bandai JP One Piece cardlist | No automated scrape; EN via TCGCSV + apitcg | Stage dumps: `pokedb fetch-bandai-onepiece` / `data/raw/bandai_onepiece/` |
| Weiss Schwarz Japanese | TCGplayer EN releases only | `pokedb fetch-language-dumps --target weiss_jp` → `data/raw/weiss_jp/` |
| Yu-Gi-Oh! OCG Japanese | YGOPRODeck Western langs only | `pokedb fetch-language-dumps --target ygo_ocg` → `data/raw/ygo_ocg/` |
| Lorcana non-English | Lorcast is EN-centric | `pokedb fetch-language-dumps --target lorcana_i18n` → `data/raw/lorcana_i18n/` |

Do not block the grading workflow on live publisher scrapes — stage normalized
JSON dumps (same pattern as TCDB / Beckett) and rebuild.

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

These categories have **no structured catalog API** as of 2026. Do not block
Phases 0–4 or the grading workflow on them — track as manual curation, sports-style
xlsx/JSON imports, or a future commercial partnership.

| Category | Strategy | Notes |
| --- | --- | --- |
| Bandai Carddass (vintage DBZ, etc.) | Community wiki / curated spreadsheet | Seed sample: `1989 BANDAI CARDDASS…` in `seed.json` |
| Meiji promotional cards | Collector spreadsheets | Seed sample: `1998 MEIJI POKEMON GET CARD` |
| Skybox vintage | TCDB dumps (partial) + curated sports xlsx | Seed has 1996-97 Premium sample |
| Marvel trading cards (Fleer / Skybox / UD) | Sports-style curation | Seed sample: `1992 MARVEL UNIVERSE SERIES 1` (**not** Dice Masters) |
| Warhammer beyond Champions TCG | Skip TCGplayer cats 39–45 | Miniatures / paints / books — not cards |
| UFC / multi-sport Topps–Panini gaps | Beckett + curated spine | Expand `sports_cards.xlsx` / seed as needed |

### Commercial vendor evaluation (optional)

If scrape maintenance (TCDB / Beckett adapters) becomes too costly, evaluate a
licensed catalog (e.g. CardSight or similar) against:

1. Coverage of soccer / wrestling / football parallels we grade today
2. Stable IDs we can map into `card_uid` (`sports:…#num#parallel`)
3. Redistribution terms compatible with an **internal** grading tool

Until then, curated `sources/sports_*.xlsx` remains the spine of record.

## Vintage / no-API dumps (same pattern as sports)

Skybox, Bandai Carddass, Meiji, vintage Marvel trading cards, and non-Champions
Warhammer use the **same** ingest path as sports — not new loaders:

1. Add checklist rows to `sources/sports_cards.xlsx` / `sports_database.xlsx`, or
2. Drop JSON under `data/raw/sports/` (see `seed.json`, which already includes a
   Skybox basketball sample) / `data/raw/tcdb/` / `data/raw/beckett/`.

Do not invent a separate vintage pipeline. Carddass / Meiji / Fleer Marvel stay
manual until a commercial dump is licensed.

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
