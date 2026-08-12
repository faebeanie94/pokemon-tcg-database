# AGENTS.md

## Cursor Cloud specific instructions

This is a **Next.js 15 (App Router) + TypeScript** app — the card catalog and
matching backend for a Pokémon card grading workflow — over a local **SQLite**
database via `better-sqlite3`, styled with Tailwind CSS. Single service, no
separate backend.

### Running / testing / building

Standard scripts in `package.json` (`dev`, `build`, `start`, `lint`, `test`),
plus `import:catalog`. Use `pnpm`:

- `pnpm import:catalog` — load the Excel workbooks into SQLite. **Run this
  first**; without it every query returns nothing.
- `pnpm dev` — dev server on http://localhost:3000
- `pnpm lint` / `pnpm test` / `pnpm build`

### Non-obvious notes

- **The database is built by an importer, not seeded.** `getDb()` in
  `src/lib/db.ts` creates the schema but inserts no data, so a fresh checkout
  serves an empty catalog until `pnpm import:catalog` runs. It reads the
  `.xlsx` files at the repo root and writes `data/catalog.db` (git-ignored).
  `--reset` deletes and rebuilds; note the `-wal` and `-shm` files that WAL mode
  also creates.
- **Normalized keys are stored, so changing a normalizer means re-importing.**
  `src/lib/normalize.ts` derives the comparison keys (`name_norm`,
  `card_number_norm`, and so on) that queries compare against. If you change a
  rule there, rows imported under the old rule will silently stop matching
  until `pnpm import:catalog --reset` is run.
- **Accent folding is confined to Latin runs on purpose.** Unicode classes the
  Japanese dakuten and long-vowel mark as diacritics, so folding accents
  globally turns リザードン into リサトン and makes different Japanese names
  compare equal. `src/lib/normalize.test.ts` guards this.
- **Search depends on FTS5's trigram tokenizer** (`cards_fts` in
  `src/lib/catalog.ts`), which is what makes partial CJK names findable. Queries
  shorter than three characters cannot use it and fall back to a `LIKE` scan —
  see `isTrigramSearchable`. After bulk inserts the index needs
  `rebuildSearchIndex`.
- **Set resolution happens before number parsing** in `src/lib/match.ts`. A
  token like `SV1a` is a set code while `TG01` is a collector number, and only
  the catalog can tell them apart, so the parser in `src/lib/query.ts`
  deliberately leaves ambiguous tokens alone rather than guessing.
- **The app's normalizers are registered as SQL functions** (`norm_name`,
  `norm_number` via `registerSqlFunctions`) so bulk updates derive keys with the
  same code the query path uses instead of an approximation in SQL.
- **`better-sqlite3` is a native module.** It compiles on install (gcc/make
  required, already present) and must not be bundled by Next — handled by
  `serverExternalPackages: ["better-sqlite3"]` in `next.config.mjs`. Removing
  that breaks every server route.
- **pnpm build-script approval.** `better-sqlite3` needs its install script;
  it is pre-approved via `pnpm.onlyBuiltDependencies`. The ignored-build-script
  warnings for `esbuild` / `sharp` / `unrs-resolver` are harmless here.
- **The Excel readers differ by file size.** Large workbooks are streamed, and
  the streaming reader does **not** expose real sheet names, so sheets are
  identified by their header row (`pickHandler` in `scripts/import-catalog.ts`).
  `database.xlsx` is read whole because its sheet *names* carry the language.
- **Export API keys come from the environment** (`PIKAQIAN_API_KEY`,
  `POKEWALLET_API_KEY`, `POKEMONTCGIO_API_KEY`) — see `.env.example`. Earlier
  commits hard-coded live keys in `apis/*.py`; do not reintroduce that.
- **Tests use an in-memory catalog** built by `src/lib/__fixtures__/catalog.ts`,
  which deliberately includes the cases that make matching hard (one printing
  in several languages, two sets sharing a collector number, a set code shaped
  like a card number).
