import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import { initSchema, seedIfEmpty } from "./cards";

let dbInstance: Database.Database | null = null;

function resolveDbPath(): string {
  const configured = process.env.DATABASE_PATH;
  if (configured) return configured;
  return path.join(process.cwd(), "data", "pokemon.db");
}

/**
 * Returns a lazily-initialized singleton SQLite connection. The schema is
 * created and seed data inserted on first access so the app is usable
 * immediately after a fresh checkout with no manual migration step.
 */
export function getDb(): Database.Database {
  if (dbInstance) return dbInstance;

  const dbPath = resolveDbPath();
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });

  const db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  initSchema(db);
  seedIfEmpty(db);

  dbInstance = db;
  return db;
}
