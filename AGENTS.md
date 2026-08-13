# AGENTS.md

## Cursor Cloud specific instructions

Two services over **one** SQLite database, for a **multi-game** card grading
workflow (Pokémon TCG, other TCGs, and sports / entertainment cards):

- **`src/pokedb`** — Python. Builds the card database from spreadsheets, TCGdex,
  TCGCSV, Scryfall, YGOPRODeck, Lorcast, GoAgain, apitcg, and curated sports
  seeds. This is the only thing that writes the `sets` and `cards` tables.
- **`src/app`, `src/lib`** — **Next.js 15 (App Router) + TypeScript**, with
  Tailwind CSS and `better-sqlite3`. Card matching API and operator console. It
  reads the same database and never writes card data.

The database is `build/pokemon_tcg.sqlite` (git-ignored), overridable with
`POKEDB_DB`, which both services read.

See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) for which categories have APIs
vs need curated spreadsheets.

### Running / testing / building

```bash
pip install -r requirements-dev.txt
PYTHONPATH=src python3 -m pokedb update          # TCGdex + build (default)
PYTHONPATH=src python3 -m pokedb fetch --source tcgcsv --game onepiece
PYTHONPATH=src python3 -m pokedb fetch --source scryfall
PYTHONPATH=src python3 -m pokedb build
PYTHONPATH=src pytest -q

pnpm install
pnpm build:index
pnpm dev                                         # http://localhost:3000
pnpm lint / pnpm test / pnpm build
pnpm refresh
```

`PYTHONPATH=src` is required for every `pokedb` command; there is no installed
package.

### Non-obvious notes

- **Nothing works until the card data is built.** `getDb()` throws if
  `build/pokemon_tcg.sqlite` is absent. Run `python -m pokedb update`.
- **Do not delete `data/`.** It holds `data/raw/` fetches and
  `data/raw/sports/seed.json` (curated sports checklists). Removing raw TCGdex
  dumps silently shrinks the Pokémon catalog until `pokedb fetch` runs again.
- **Games are first-class.** Schema has a `games` table; `sets.game` /
  `cards.game` scope identity and matching. Sports fields include
  `manufacturer`, `sport`, `product_year`, `subject_name`, `parallel`,
  `notations`, `serial_number`, `print_run`, `display_name`.
- **Source IDs are generic.** Use `set_source_ids(set_uid, source, source_id)`
  instead of hard-coded `tcgdex_set_id` / `pikaqian_set_id` columns.
- **Card identity is `card_uid`**,
  `'<game>:<language>:<set slug>#<number>[#<parallel>]'` such as
  `pokemon:en:bs#4` or
  `sports:en:2025-26-topps-manchester-united-team-set#38#haloref`.
  Legacy UIDs without the game prefix (`en:bs#4`) are still accepted by the
  matcher during migration. Grading records should store the new form going
  forward.
- **Sports grading format** (operator / API fields): set name, card name line
  (subject + parallel + notations + optional `09/15` serial), number. The
  `09/15` serial is a print run, **not** a Pokémon-style printed total — see
  `src/lib/sports.ts`.
- **Sports data strategy** defaults to curated JSON/xlsx (no public Topps /
  Panini / Upper Deck checklist API). Seed examples live in
  `data/raw/sports/seed.json`.
- **The match index is derived and self-healing.** `match_cards`, `match_sets`
  and `cards_fts` are rebuilt by TypeScript (`buildMatchIndex`) when stale.
- **Normalized keys are stored.** After changing a normalizer, run
  `pnpm build:index`. Sports numbers use `normalizeSportsNumber` (keeps
  hyphens in `SSL-SM`).
- **Accent folding is confined to Latin runs** — see `normalize.test.ts`.
- **Search depends on FTS5's trigram tokenizer**; short queries fall back to
  `LIKE` — see `isTrigramSearchable`.
- **Set resolution happens before number parsing** for TCG free text.
- **SQL normalizers** (`norm_name`, `norm_number`, `norm_sports_number`) are
  registered via `registerSqlFunctions`.
- **`better-sqlite3`** must stay in `serverExternalPackages`.
- **pnpm build-script approval** via `pnpm.onlyBuiltDependencies`.
- **The TypeScript test fixture loads the real `src/pokedb/schema.sql`** and
  includes Pokémon hard cases plus Beckham / Michaels sports rows.
- **Export API keys** from the environment (`PIKAQIAN_API_KEY`,
  `POKEWALLET_API_KEY`, `POKEMONTCGIO_API_KEY`) — see `.env.example`. TCGCSV,
  Scryfall, YGOPRODeck, Lorcast and GoAgain need no key.
- **Licensing:** Bandai / Konami / Ravensburger / Topps / Panini assert rights
  over card data and images. Fine for an internal grading tool; do not
  republish catalogs without a license.
- **`apis/tcgdex_export.py`'s `id` column feeds `pokedb verify`**. Renaming it
  makes verify silently report zero rows. Additional exporters:
  `apis/tcgcsv_export.py`, `apis/scryfall_export.py`,
  `apis/ygoprodeck_export.py`.
