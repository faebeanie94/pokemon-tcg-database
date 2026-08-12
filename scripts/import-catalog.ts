/**
 * Loads the exported workbooks into the SQLite catalog the app serves.
 *
 * Run with `pnpm import:catalog`. Every known workbook in the working
 * directory is imported; missing ones are skipped, so this works before the
 * pokemontcg.io and PokeWallet exports exist.
 *
 * Sheets are identified by their header row rather than their name, because
 * the streaming reader used for the large workbooks does not expose sheet
 * names. That also means a renamed sheet still imports correctly.
 */

import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";
import ExcelJS from "exceljs";
import { insertSetAliases, type SetAlias } from "../src/lib/aliases";
import {
  backfillFromSets,
  countCards,
  initSchema,
  insertCards,
  insertSets,
  rebuildSearchIndex,
  type CatalogCardInput,
  type CatalogSet,
} from "../src/lib/catalog";
import { normalizeName } from "../src/lib/normalize";
import { resolveDbPath } from "../src/lib/db";

const BATCH_SIZE = 5_000;

type Row = Record<string, string>;

interface ImportSummary {
  file: string;
  cards: number;
  sets: number;
  aliases: number;
  notes: string[];
}

async function main() {
  const args = process.argv.slice(2);
  const reset = args.includes("--reset");
  const files = args.filter((a) => !a.startsWith("--"));

  const dbPath = resolveDbPath();
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });

  if (reset) {
    for (const suffix of ["", "-wal", "-shm"]) {
      fs.rmSync(`${dbPath}${suffix}`, { force: true });
    }
    console.log(`Removed existing database at ${dbPath}`);
  }

  const db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  initSchema(db);

  const targets = files.length ? files : defaultTargets();
  const summaries: ImportSummary[] = [];

  for (const file of targets) {
    if (!fs.existsSync(file)) {
      console.log(`- ${file}: not found, skipping`);
      continue;
    }
    console.log(`\n=== ${file} ===`);
    summaries.push(await importWorkbook(db, file));
  }

  console.log("\nFilling in card fields from set metadata...");
  console.log(`  ${backfillFromSets(db)} card rows updated`);

  console.log("Rebuilding the search index...");
  rebuildSearchIndex(db);

  console.log("\n--- Summary ---");
  for (const s of summaries) {
    console.log(
      `${s.file}: ${s.cards} cards, ${s.sets} sets, ${s.aliases} set aliases`
    );
    for (const note of s.notes) console.log(`    ${note}`);
  }
  console.log(`\nCatalog now holds ${countCards(db)} cards at ${dbPath}`);
  db.close();
}

function defaultTargets(): string[] {
  return [
    "tcgdex_cards.xlsx",
    "pikaqian_cards.xlsx",
    "pokemontcgio_cards.xlsx",
    "pokewallet_cards.xlsx",
    "database.xlsx",
  ];
}

async function importWorkbook(
  db: Database.Database,
  file: string
): Promise<ImportSummary> {
  // The curated set workbook needs real sheet names to tell languages apart,
  // and it is small enough to read whole.
  if (path.basename(file).toLowerCase() === "database.xlsx") {
    return importCuratedSets(db, file);
  }
  return importCardWorkbook(db, file);
}

/**
 * Streams a card workbook, dispatching each sheet to a handler chosen by its
 * header row.
 */
async function importCardWorkbook(
  db: Database.Database,
  file: string
): Promise<ImportSummary> {
  const summary: ImportSummary = { file, cards: 0, sets: 0, aliases: 0, notes: [] };

  const reader = new ExcelJS.stream.xlsx.WorkbookReader(file, {
    sharedStrings: "cache",
    worksheets: "emit",
    hyperlinks: "ignore",
    styles: "ignore",
  });

  for await (const worksheet of reader as AsyncIterable<ExcelJS.Worksheet>) {
    let header: string[] | null = null;
    let handler: SheetHandler | null = null;
    let batch: Row[] = [];
    let rowCount = 0;

    for await (const row of worksheet as unknown as AsyncIterable<ExcelJS.Row>) {
      const values = row.values as unknown[];
      if (!header) {
        header = values.slice(1).map((v) => String(v ?? "").trim());
        handler = pickHandler(header);
        if (!handler) {
          summary.notes.push(`unrecognised sheet [${header.slice(0, 4).join(", ")}]`);
          break;
        }
        continue;
      }

      batch.push(toRow(header, values));
      rowCount += 1;

      if (batch.length >= BATCH_SIZE) {
        handler!.write(db, batch, summary);
        batch = [];
      }
    }

    if (handler && batch.length) handler.write(db, batch, summary);
    if (handler && rowCount) {
      console.log(`  ${handler.label}: ${rowCount} rows`);
    }
  }

  return summary;
}

interface SheetHandler {
  label: string;
  write(db: Database.Database, rows: Row[], summary: ImportSummary): void;
}

/** Chooses a handler by looking for the columns each source is known by. */
function pickHandler(header: string[]): SheetHandler | null {
  const has = (...cols: string[]) => cols.every((c) => header.includes(c));

  if (has("language", "set_id", "card_number", "card_id", "name")) {
    return TCGDEX_CARDS;
  }
  if (has("language", "set_id", "set_name", "release_date")) {
    return TCGDEX_SETS;
  }
  if (has("card_number", "name", "local_name", "card_set_id")) {
    return PIKAQIAN_CARDS;
  }
  if (has("id", "name", "local_name", "series")) {
    return PIKAQIAN_SETS;
  }
  if (has("id", "name", "number", "set_name", "set_series")) {
    return POKEMONTCGIO_CARDS;
  }
  if (has("id", "name", "set_name", "set_code", "card_number", "set_language")) {
    return POKEWALLET_CARDS;
  }
  return null;
}

const TCGDEX_CARDS: SheetHandler = {
  label: "TCGdex cards",
  write(db, rows, summary) {
    const cards: CatalogCardInput[] = rows
      .filter((r) => r.card_id && r.name)
      .map((r) => ({
        source: "tcgdex",
        source_card_id: r.card_id,
        language: r.language,
        set_id: r.set_id,
        set_name: r.set_name,
        set_abbreviation: r.set_abbreviation || null,
        series_name: r.series_name || null,
        printed_total: toInt(r.printed_total),
        card_number: r.card_number,
        name: r.name,
        english_name: r.english_name || null,
      }));
    summary.cards += insertCards(db, cards);
  },
};

const TCGDEX_SETS: SheetHandler = {
  label: "TCGdex sets",
  write(db, rows, summary) {
    const sets: CatalogSet[] = rows
      .filter((r) => r.set_id)
      .map((r) => ({
        source: "tcgdex",
        language: r.language,
        set_id: r.set_id,
        set_name: r.set_name,
        local_name: null,
        set_abbreviation: r.set_abbreviation || null,
        series_name: r.series_name || null,
        release_date: r.release_date || null,
        printed_total: toInt(r.printed_total),
        card_count_total: toInt(r.card_count_total),
      }));
    summary.sets += insertSets(db, sets);
  },
};

/**
 * PikaQian covers Simplified Chinese only. Its `name` is the English name and
 * `local_name` the Chinese one, which is exactly the cross-language link
 * TCGdex cannot provide for Chinese sets.
 */
const PIKAQIAN_CARDS: SheetHandler = {
  label: "PikaQian cards",
  write(db, rows, summary) {
    const cards: CatalogCardInput[] = rows
      .filter((r) => r.id && (r.local_name || r.name))
      .map((r) => ({
        source: "pikaqian",
        source_card_id: r.id,
        language: "zh-cn",
        set_id: r.card_set_id,
        set_name: r.card_set_id,
        set_abbreviation: r.card_set_id || null,
        series_name: null,
        printed_total: null,
        card_number: r.card_number,
        name: r.local_name || r.name,
        english_name: r.name || null,
      }));
    summary.cards += insertCards(db, cards);
  },
};

const PIKAQIAN_SETS: SheetHandler = {
  label: "PikaQian sets",
  write(db, rows, summary) {
    const sets: CatalogSet[] = rows
      .filter((r) => r.id)
      .map((r) => ({
        source: "pikaqian",
        language: "zh-cn",
        set_id: r.id,
        set_name: r.name || r.id,
        local_name: r.local_name || null,
        set_abbreviation: r.id,
        series_name: r.series || null,
        release_date: r.release_date || null,
        printed_total: null,
        card_count_total: toInt(r["card_count.actual"]),
      }));
    summary.sets += insertSets(db, sets);

    const aliases: SetAlias[] = [];
    for (const row of sets) {
      if (row.local_name) {
        aliases.push({
          language: row.language,
          set_id: row.set_id,
          alias: row.local_name,
          source: "pikaqian",
        });
      }
      if (row.set_name && row.set_name !== row.set_id) {
        aliases.push({
          language: row.language,
          set_id: row.set_id,
          alias: row.set_name,
          source: "pikaqian",
        });
      }
    }
    summary.aliases += insertSetAliases(db, aliases);
  },
};

/**
 * pokemontcg.io has no set ID column, but its card IDs are "<set>-<number>",
 * and those set IDs line up with TCGdex's for most sets.
 */
const POKEMONTCGIO_CARDS: SheetHandler = {
  label: "pokemontcg.io cards",
  write(db, rows, summary) {
    const cards: CatalogCardInput[] = rows
      .filter((r) => r.id && r.name)
      .map((r) => ({
        source: "pokemontcgio",
        source_card_id: r.id,
        language: "en",
        set_id: r.id.includes("-") ? r.id.slice(0, r.id.lastIndexOf("-")) : r.id,
        set_name: r.set_name,
        set_abbreviation: null,
        series_name: r.set_series || null,
        printed_total: null,
        card_number: r.number,
        name: r.name,
        english_name: r.name,
      }));
    summary.cards += insertCards(db, cards);
  },
};

const POKEWALLET_CARDS: SheetHandler = {
  label: "PokeWallet cards",
  write(db, rows, summary) {
    const cards: CatalogCardInput[] = rows
      .filter((r) => r.id && r.name)
      .map((r) => ({
        source: "pokewallet",
        source_card_id: r.id,
        language: r.set_language || "en",
        set_id: r.set_code || r.set_name,
        set_name: r.set_name,
        set_abbreviation: r.set_code || null,
        series_name: null,
        printed_total: null,
        card_number: r.card_number,
        name: r.name,
        english_name: r.clean_name || r.name,
      }));
    summary.cards += insertCards(db, cards);
  },
};

const CURATED_SHEET_LANGUAGES: Record<string, string> = {
  "english sets": "en",
  "japanese sets": "ja",
  "simplified chinese sets": "zh-cn",
};

/**
 * The curated workbook lists sets by English name with a house abbreviation.
 * It has no set IDs, so each row is tied to a catalog set by matching the
 * abbreviation against a known set ID (how the Chinese sets are coded) or by
 * matching the English set name. Rows that match nothing are counted and
 * reported rather than guessed at.
 */
async function importCuratedSets(
  db: Database.Database,
  file: string
): Promise<ImportSummary> {
  const summary: ImportSummary = { file, cards: 0, sets: 0, aliases: 0, notes: [] };

  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.readFile(file);

  const setsByIdLower = new Map<string, { language: string; set_id: string }[]>();
  const setsByNameNorm = new Map<string, { language: string; set_id: string }[]>();
  for (const row of db
    .prepare("SELECT language, set_id, set_name_norm FROM sets")
    .all() as { language: string; set_id: string; set_name_norm: string }[]) {
    push(setsByIdLower, row.set_id.toLowerCase(), row);
    push(setsByNameNorm, row.set_name_norm, row);
  }

  workbook.eachSheet((worksheet) => {
    const language = CURATED_SHEET_LANGUAGES[worksheet.name.trim().toLowerCase()];
    if (!language) {
      summary.notes.push(`sheet "${worksheet.name}": unknown language, skipped`);
      return;
    }

    const aliases: SetAlias[] = [];
    let unmatched = 0;
    let total = 0;

    worksheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;
      const values = row.values as unknown[];
      const setName = String(values[2] ?? "").trim();
      const abbreviation = String(values[3] ?? "").trim();
      if (!setName) return;
      total += 1;

      const matches =
        (abbreviation && setsByIdLower.get(abbreviation.toLowerCase())) ||
        setsByNameNorm.get(normalizeName(setName)) ||
        [];
      const inLanguage = matches.filter((m) => m.language === language);
      if (!inLanguage.length) {
        unmatched += 1;
        return;
      }

      for (const match of inLanguage) {
        if (abbreviation) {
          aliases.push({
            language,
            set_id: match.set_id,
            alias: abbreviation,
            source: "curated",
          });
        }
        // The English name is itself a useful alias for a non-English set.
        aliases.push({
          language,
          set_id: match.set_id,
          alias: setName,
          source: "curated",
        });
      }
    });

    summary.aliases += insertSetAliases(db, aliases);
    console.log(
      `  ${worksheet.name} (${language}): ${total - unmatched}/${total} rows tied to a set`
    );
    if (unmatched) {
      summary.notes.push(
        `${worksheet.name}: ${unmatched} of ${total} rows matched no catalog set`
      );
    }
  });

  return summary;
}

function push<T>(map: Map<string, T[]>, key: string, value: T): void {
  const existing = map.get(key);
  if (existing) existing.push(value);
  else map.set(key, [value]);
}

function toRow(header: string[], values: unknown[]): Row {
  const row: Row = {};
  header.forEach((column, index) => {
    if (!column) return;
    const value = values[index + 1];
    row[column] = value === null || value === undefined ? "" : String(value).trim();
  });
  return row;
}

function toInt(value: string | undefined): number | null {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.round(parsed) : null;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
