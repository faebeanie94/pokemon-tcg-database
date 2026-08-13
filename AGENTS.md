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
vs need curated spreadsheets, [docs/MIGRATION.md](docs/MIGRATION.md) for
`card_uid` cutover, and [docs/SPORTS.md](docs/SPORTS.md) for sports checklists.

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
pnpm refresh                                     # TCGdex only + build + match index
pnpm refresh:games                                # also TCGCSV / YGO / Lorcast / GoAgain / apitcg
pnpm fetch:mtg / pnpm fetch:onepiece             # large or game-specific dumps
```

`PYTHONPATH=src` is required for every `pokedb` command; there is no installed
package. **`pnpm refresh` stays Pokémon-first** on purpose — Scryfall and full
TCGCSV walks are opt-in. See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

### Non-obvious notes

- **Nothing works until the card data is built.** `getDb()` throws if
  `build/pokemon_tcg.sqlite` is absent, deliberately, rather than serving an
  empty catalog. Run `python -m pokedb update`.
- **Do not delete `data/`.** It holds `data/raw/` fetches and
  `data/raw/sports/seed.json` (curated sports checklists). Removing raw TCGdex
  dumps silently shrinks the Pokémon catalog until `pokedb fetch` runs again.
- **Games are first-class.** Schema has a `games` table (`kind`: `tcg` /
  `sports` / `non_sport`); `sets.game` / `cards.game` scope identity and
  matching. Sports fields include `manufacturer`, `sport`, `product_year`,
  `subject_name`, `parallel`, `notations`, `serial_number`, `print_run`,
  `display_name`. Language `und` is the language-neutral row; sports checklists
  still use `en` when the printed label is English.
- **Source IDs are generic.** Use `set_source_ids(set_uid, source, source_id)`
  instead of hard-coded `tcgdex_set_id` / `pikaqian_set_id` columns. The match
  index also tokens `set_sources.source_set_id`.
- **Card identity is `card_uid`**,
  `'<game>:<language>:<set slug>#<number>[#<parallel>]'` such as
  `pokemon:en:bs#4`, `mtg:zhs:lea#1`, or
  `sports:en:202526toppsmanchesterunitedteamset#38#haloref`.
  Language may be 2–3 letters (`zhs`, `und`). Legacy UIDs without the game
  prefix (`en:bs#4`) are still accepted by the matcher during migration.
  Grading records should store the new form going forward. See
  [docs/MIGRATION.md](docs/MIGRATION.md).
- **Sports grading format** (operator / API fields): set name, card name line
  (subject + parallel + notations + optional `09/15` serial), number. The
  `09/15` serial is a print run, **not** a Pokémon-style printed total — see
  `src/lib/sports.ts`.
- **Sports data strategy** defaults to curated xlsx/JSON (no public Topps /
  Panini / Upper Deck checklist API). Spine:
  `sources/sports_database.xlsx` + `sources/sports_cards.xlsx` (regenerate with
  `python3 scripts/seed_sports_xlsx.py`). Broader examples live in
  `data/raw/sports/seed.json`. Optional TCDB/Beckett dumps go under
  `data/raw/tcdb/` / `data/raw/beckett/` via `apis/tcdb_fetch.py` /
  `apis/beckett_fetch.py`.
- **The match index is derived and self-healing.** `match_cards`, `match_sets`
  and `cards_fts` live in the same file as the canonical tables but are built by
  the TypeScript side (`buildMatchIndex` in `src/lib/catalog.ts`). A `pokedb
  build` leaves them stale, and the API's timer refresh swaps in a file without
  them, so `getDb()` compares `match_index_info.built_for` against
  `build_info.built_at` and rebuilds when they differ. Never hand-edit them.
- **Normalized keys are stored, so changing a normalizer means rebuilding the
  index.** After changing a rule, run `pnpm build:index`. Sports numbers use
  `normalizeSportsNumber` (keeps hyphens in `SSL-SM`).
- **Accent folding is confined to Latin runs on purpose.** Unicode classes the
  Japanese dakuten and long-vowel mark as diacritics, so folding globally turns
  リザードン into リサトン and makes different Japanese names compare equal.
  `src/lib/normalize.test.ts` guards this. `normalize_name` in
  `src/pokedb/normalize.py` still has this bug, but it only folds *set* names
  there, where the impact is narrower.
- **Search depends on FTS5's trigram tokenizer**, which is what makes partial CJK
  names findable. Queries under three characters cannot use it and fall back to a
  `LIKE` scan — see `isTrigramSearchable`.
- **Set resolution happens before number parsing** in `src/lib/match.ts` for TCG
  free text. A token like `SV1a` is a set code while `TG01` is a collector
  number, and only the catalog can tell them apart, so `src/lib/query.ts`
  deliberately leaves ambiguous tokens alone rather than guessing.
- **The app's normalizers are registered as SQL functions** (`norm_name`,
  `norm_number`, `norm_sports_number` via `registerSqlFunctions`) so the index
  is built with the same code the query path uses instead of an approximation
  in SQL.
- **`better-sqlite3` is a native module.** It compiles on install (gcc/make
  required, already present) and must not be bundled by Next — handled by
  `serverExternalPackages: ["better-sqlite3"]` in `next.config.mjs`. Removing
  that breaks every server route.
- **pnpm build-script approval.** `better-sqlite3` needs its install script; it
  is pre-approved via `pnpm.onlyBuiltDependencies`. The ignored-build-script
  warnings for `esbuild` / `sharp` / `unrs-resolver` are harmless here.
- **The TypeScript test fixture loads the real `src/pokedb/schema.sql`**
  (`src/lib/__fixtures__/catalog.ts`), so the tests fail if the two sides drift
  apart instead of passing against a hand-copied schema. Its rows include
  Pokémon hard cases plus Beckham / Michaels sports rows.
- **Export API keys come from the environment** (`PIKAQIAN_API_KEY`,
  `POKEWALLET_API_KEY`, `POKEMONTCGIO_API_KEY`) — see `.env.example`. TCGCSV,
  Scryfall, YGOPRODeck, Lorcast and GoAgain need no key. Earlier commits
  hard-coded live keys in `apis/*.py`; do not reintroduce that.
- **Licensing:** Bandai, Konami, Ravensburger, Wizards, Topps, and Panini assert
  rights over card data and images. Fine for an **internal grading tool**; do
  not republish catalogs without a license.
- **`apis/tcgdex_export.py`'s `id` column feeds `pokedb verify`**, which compares
  `tcgdex_cards.xlsx` against a fresh download. Renaming it makes verify
  silently report zero rows instead of failing. Additional exporters:
  `apis/tcgcsv_export.py`, `apis/scryfall_export.py`,
  `apis/ygoprodeck_export.py`.
- **Bandai JP One Piece** scrape is deferred; English One Piece comes from
  TCGCSV + apitcg (`pnpm fetch:onepiece`).
