/**
 * Builds the derived match index inside the canonical card database.
 *
 * Run with `pnpm build:index`, after `python -m pokedb build` has produced the
 * database. The app also rebuilds the index by itself when it finds one missing
 * or out of date, so this is mainly for doing the work up front rather than on
 * the first request.
 */

import fs from "node:fs";
import Database from "better-sqlite3";
import {
  buildMatchIndex,
  canonicalBuiltAt,
  countCards,
  isCatalogBuilt,
} from "../src/lib/catalog";
import { resolveDbPath } from "../src/lib/db";

function main() {
  const dbPath = resolveDbPath();
  if (!fs.existsSync(dbPath)) {
    console.error(
      `No card database at ${dbPath}.\n` +
        "Build it first with: PYTHONPATH=src python3 -m pokedb update"
    );
    process.exit(1);
  }

  const db = new Database(dbPath);
  db.pragma("journal_mode = WAL");

  if (!isCatalogBuilt(db)) {
    console.error(
      `${dbPath} has no cards/sets tables.\n` +
        "Build the card data first with: PYTHONPATH=src python3 -m pokedb update"
    );
    process.exit(1);
  }

  console.log(`Database:   ${dbPath}`);
  console.log(`Card data:  ${countCards(db)} cards, built ${canonicalBuiltAt(db)}`);

  const started = Date.now();
  const stats = buildMatchIndex(db);
  const seconds = ((Date.now() - started) / 1000).toFixed(1);

  console.log(
    `Match index: ${stats.cards} cards, ${stats.setTokens} set tokens, in ${seconds}s`
  );
  db.close();
}

main();
