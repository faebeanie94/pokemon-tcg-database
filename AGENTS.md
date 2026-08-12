# AGENTS.md

## Cursor Cloud specific instructions

This is a **Next.js 15 (App Router) + TypeScript** app — a Pokémon TCG card
database — backed by a local **SQLite** database via `better-sqlite3`, styled
with Tailwind CSS. It is a single service; there is no separate backend.

### Running / testing / building

Standard scripts are defined in `package.json` (`dev`, `build`, `start`,
`lint`, `test`). Use `pnpm`:

- `pnpm dev` — dev server on http://localhost:3000 (hot reload)
- `pnpm lint` / `pnpm test` / `pnpm build`

### Non-obvious notes

- **Database is auto-created, not migrated.** The SQLite file lives at
  `data/pokemon.db` and is created + seeded automatically on first DB access
  (see `src/lib/db.ts` → `getDb()`). It is git-ignored. To reset the catalog to
  the seed data, stop the dev server and delete `data/pokemon.db*` (the `*`
  matters — WAL mode also writes `-wal` and `-shm` files).
- **`better-sqlite3` is a native module.** It compiles on install (gcc/make
  required, already present). It must NOT be bundled by Next — this is handled
  by `serverExternalPackages: ["better-sqlite3"]` in `next.config.mjs`. Don't
  remove that or server routes will fail to load the native binding.
- **pnpm build-script approval.** `better-sqlite3` needs its install script to
  run; it is pre-approved via `pnpm.onlyBuiltDependencies` in `package.json` so
  `pnpm install` is non-interactive. The ignored-build-script warnings for
  `esbuild` / `sharp` / `unrs-resolver` are harmless here (tests, lint, and dev
  all work without them; `next/image` optimization is not used).
- **DB path override.** Set `DATABASE_PATH` to point the app at a different
  SQLite file (used by nothing by default; tests use an in-memory DB directly).
- The data-access layer in `src/lib/cards.ts` takes a `Database` instance as an
  argument, which is what makes it unit-testable with an in-memory DB in
  `src/lib/cards.test.ts`.
