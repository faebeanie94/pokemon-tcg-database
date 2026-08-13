# AGENTS.md

## Cursor Cloud specific instructions

Two services over **one** SQLite database, for a Pokémon card grading workflow:

- **`src/pokedb`** — Python. Builds the card database from the spreadsheets, the
  TCGdex API and PokéAPI, and serves it with FastAPI. This is the only thing
  that writes the `sets` and `cards` tables.
- **`src/app`, `src/lib`** — **Next.js 15 (App Router) + TypeScript**, with
  Tailwind CSS and `better-sqlite3`. Card matching API and operator console. It
  reads the same database and never writes card data.

The database is `build/pokemon_tcg.sqlite` (git-ignored), overridable with
`POKEDB_DB`, which both services read.

### Running / testing / building

```bash
pip install -r requirements-dev.txt
PYTHONPATH=src python3 -m pokedb update    # build the card data — do this first
PYTHONPATH=src pytest -q                   # python tests

pnpm install
pnpm build:index                           # derive the match index
pnpm dev                                   # http://localhost:3000
pnpm lint / pnpm test / pnpm build
pnpm refresh                               # rebuild card data + match index
```

`PYTHONPATH=src` is required for every `pokedb` command; there is no installed
package.

### Non-obvious notes

- **Nothing works until the card data is built.** `getDb()` throws if
  `build/pokemon_tcg.sqlite` is absent, deliberately, rather than serving an
  empty catalog. Run `python -m pokedb update`.
- **Do not delete `data/`.** It looks like a stale app directory but holds
  `data/raw/`, the fetched TCGdex payloads the build reads. Removing it silently
  drops the build from ~145k cards to ~12k until `pokedb fetch` runs again.
- **The match index is derived and self-healing.** `match_cards`, `match_sets`
  and `cards_fts` live in the same file as the canonical tables but are built by
  the TypeScript side (`buildMatchIndex` in `src/lib/catalog.ts`). A `pokedb
  build` leaves them stale, and the API's timer refresh swaps in a file without
  them, so `getDb()` compares `match_index_info.built_for` against
  `build_info.built_at` and rebuilds when they differ. Never hand-edit them.
- **Normalized keys are stored, so changing a normalizer means rebuilding the
  index.** `src/lib/normalize.ts` derives the keys queries compare against. After
  changing a rule, run `pnpm build:index` or matching silently degrades.
- **Accent folding is confined to Latin runs on purpose.** Unicode classes the
  Japanese dakuten and long-vowel mark as diacritics, so folding globally turns
  リザードン into リサトン and makes different Japanese names compare equal.
  `src/lib/normalize.test.ts` guards this. `normalize_name` in
  `src/pokedb/normalize.py` still has this bug, but it only folds *set* names
  there, where the impact is narrower.
- **Search depends on FTS5's trigram tokenizer**, which is what makes partial CJK
  names findable. Queries under three characters cannot use it and fall back to a
  `LIKE` scan — see `isTrigramSearchable`.
- **Set resolution happens before number parsing** in `src/lib/match.ts`. A token
  like `SV1a` is a set code while `TG01` is a collector number, and only the
  catalog can tell them apart, so `src/lib/query.ts` deliberately leaves
  ambiguous tokens alone rather than guessing.
- **The app's normalizers are registered as SQL functions** (`norm_name`,
  `norm_number` via `registerSqlFunctions`) so the index is built with the same
  code the query path uses instead of an approximation in SQL.
- **Card identity is `card_uid`**, `'<language>:<set code>#<number>'` such as
  `en:bs#4` — a string, not an integer, stable across rebuilds, and what a
  grading record should store. `/api/cards/:id` takes it URL-encoded.
- **`better-sqlite3` is a native module.** It compiles on install (gcc/make
  required, already present) and must not be bundled by Next — handled by
  `serverExternalPackages: ["better-sqlite3"]` in `next.config.mjs`. Removing
  that breaks every server route.
- **pnpm build-script approval.** `better-sqlite3` needs its install script; it
  is pre-approved via `pnpm.onlyBuiltDependencies`. The ignored-build-script
  warnings for `esbuild` / `sharp` / `unrs-resolver` are harmless here.
- **The TypeScript test fixture loads the real `src/pokedb/schema.sql`**
  (`src/lib/__fixtures__/catalog.ts`), so the tests fail if the two sides drift
  apart instead of passing against a hand-copied schema. Its rows deliberately
  include the hard cases: one printing in several languages, two English sets
  sharing the code `BS`, and a Japanese set code shaped like a card number.
- **Export API keys come from the environment** (`PIKAQIAN_API_KEY`,
  `POKEWALLET_API_KEY`, `POKEMONTCGIO_API_KEY`) — see `.env.example`. Earlier
  commits hard-coded live keys in `apis/*.py`; do not reintroduce that.
- **`apis/tcgdex_export.py`'s `id` column feeds `pokedb verify`**, which compares
  `tcgdex_cards.xlsx` against a fresh download. Renaming it makes verify
  silently report zero rows instead of failing.
