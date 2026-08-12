import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import { initSchema } from "./catalog";

let dbInstance: Database.Database | null = null;

export function resolveDbPath(): string {
  return (
    process.env.DATABASE_PATH ?? path.join(process.cwd(), "data", "catalog.db")
  );
}

/**
 * Lazily-initialized singleton SQLite connection.
 *
 * The schema is created on first access, but no data is seeded: the catalog is
 * loaded from the exported workbooks by `pnpm import:catalog`. A fresh checkout
 * therefore answers queries against an empty catalog rather than fabricated
 * cards, which is the safer default for a grading lookup.
 */
export function getDb(): Database.Database {
  if (dbInstance) return dbInstance;

  const dbPath = resolveDbPath();
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });

  const db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  initSchema(db);

  dbInstance = db;
  return db;
}
