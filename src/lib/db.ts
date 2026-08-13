import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import {
  buildMatchIndex,
  isCatalogBuilt,
  isIndexStale,
  registerSqlFunctions,
} from "./catalog";

let dbInstance: Database.Database | null = null;

/**
 * The single card database, built by `python -m pokedb build`. POKEDB_DB is the
 * same variable the Python service reads, so both point at one file by default.
 */
export function resolveDbPath(): string {
  return (
    process.env.POKEDB_DB ??
    process.env.DATABASE_PATH ??
    path.join(process.cwd(), "build", "pokemon_tcg.sqlite")
  );
}

/**
 * Lazily-initialized singleton connection to the card database.
 *
 * The canonical tables are read-only as far as this app is concerned. The
 * derived match index in the same file is rebuilt automatically when it is
 * missing or older than the current build, because the Python service refreshes
 * by swapping in a freshly built file that has no index in it yet.
 */
export function getDb(): Database.Database {
  if (dbInstance) return dbInstance;

  const dbPath = resolveDbPath();
  if (!fs.existsSync(dbPath)) {
    throw new Error(
      `no card database at ${dbPath}. Run \`python -m pokedb update\` to build it, ` +
        `or set POKEDB_DB to an existing build.`
    );
  }

  const db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  registerSqlFunctions(db);

  if (isCatalogBuilt(db) && isIndexStale(db)) {
    console.log("Match index is missing or out of date; rebuilding...");
    const stats = buildMatchIndex(db);
    console.log(
      `Match index built: ${stats.cards} cards, ${stats.setTokens} set tokens.`
    );
  }

  dbInstance = db;
  return db;
}
