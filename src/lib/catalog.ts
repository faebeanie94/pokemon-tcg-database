import type { Database } from "better-sqlite3";
import { initAliasSchema } from "./aliases";
import { normalizeName, normalizeNumber, normalizeSetToken } from "./normalize";
import { isTrigramSearchable } from "./query";

/**
 * The catalog: one row per card printing, per language, per source.
 *
 * This is a lookup table for a grading workflow, so it holds only the fields
 * that identify a physical card — language, set, collector number, name. No
 * gameplay data (type, HP), rarity or images.
 */
export interface CatalogCard {
  id: number;
  source: string;
  source_card_id: string;
  language: string;
  set_id: string;
  set_name: string;
  set_abbreviation: string | null;
  series_name: string | null;
  printed_total: number | null;
  card_number: string;
  name: string;
  english_name: string | null;
}

export interface CatalogSet {
  source: string;
  language: string;
  set_id: string;
  set_name: string;
  local_name: string | null;
  set_abbreviation: string | null;
  series_name: string | null;
  release_date: string | null;
  printed_total: number | null;
  card_count_total: number | null;
}

/** A row as produced by an importer, before normalized keys are derived. */
export interface CatalogCardInput {
  source: string;
  source_card_id: string;
  language: string;
  set_id: string;
  set_name: string;
  set_abbreviation?: string | null;
  series_name?: string | null;
  printed_total?: number | null;
  card_number: string;
  name: string;
  english_name?: string | null;
}

const CARD_COLUMNS = `id, source, source_card_id, language, set_id, set_name,
  set_abbreviation, series_name, printed_total, card_number, name, english_name`;

/**
 * Exposes the app's normalizers to SQL, so bulk updates derive the same keys
 * the query path compares against instead of an approximation of them.
 */
export function registerSqlFunctions(db: Database): void {
  db.function("norm_name", { deterministic: true }, (value: unknown) =>
    normalizeName(value == null ? "" : String(value))
  );
  db.function("norm_number", { deterministic: true }, (value: unknown) =>
    normalizeNumber(value == null ? "" : String(value))
  );
}

export function initSchema(db: Database): void {
  registerSqlFunctions(db);

  db.exec(`
    CREATE TABLE IF NOT EXISTS cards (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source TEXT NOT NULL,
      source_card_id TEXT NOT NULL,
      language TEXT NOT NULL,
      set_id TEXT NOT NULL,
      set_name TEXT NOT NULL,
      set_abbreviation TEXT,
      series_name TEXT,
      printed_total INTEGER,
      card_number TEXT NOT NULL,
      card_number_norm TEXT NOT NULL,
      name TEXT NOT NULL,
      name_norm TEXT NOT NULL,
      english_name TEXT,
      english_name_norm TEXT,
      set_name_norm TEXT NOT NULL,
      set_abbreviation_norm TEXT,
      UNIQUE (source, language, source_card_id)
    );

    CREATE TABLE IF NOT EXISTS sets (
      source TEXT NOT NULL,
      language TEXT NOT NULL,
      set_id TEXT NOT NULL,
      set_name TEXT NOT NULL,
      local_name TEXT,
      set_abbreviation TEXT,
      series_name TEXT,
      release_date TEXT,
      printed_total INTEGER,
      card_count_total INTEGER,
      set_name_norm TEXT NOT NULL,
      set_abbreviation_norm TEXT,
      PRIMARY KEY (source, language, set_id)
    );

    -- Lookups a grading operator actually performs: number within a set,
    -- number plus printed total, exact name, and set abbreviation.
    CREATE INDEX IF NOT EXISTS idx_cards_set_number
      ON cards (language, set_id, card_number_norm);
    CREATE INDEX IF NOT EXISTS idx_cards_number_total
      ON cards (card_number_norm, printed_total);
    CREATE INDEX IF NOT EXISTS idx_cards_name_norm ON cards (name_norm);
    CREATE INDEX IF NOT EXISTS idx_cards_english_name_norm ON cards (english_name_norm);
    CREATE INDEX IF NOT EXISTS idx_cards_set_abbr ON cards (set_abbreviation_norm);
    CREATE INDEX IF NOT EXISTS idx_cards_language ON cards (language);
    CREATE INDEX IF NOT EXISTS idx_sets_abbr ON sets (set_abbreviation_norm);

    -- Substring search over names in any script. The trigram tokenizer is what
    -- makes partial Japanese and Chinese names findable; a word tokenizer
    -- cannot split CJK text.
    CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
      name,
      english_name,
      set_name,
      content='cards',
      content_rowid='id',
      tokenize='trigram'
    );
  `);

  initAliasSchema(db);
}

/** Rebuilds the full-text index from the cards table. */
export function rebuildSearchIndex(db: Database): void {
  db.exec("INSERT INTO cards_fts(cards_fts) VALUES('rebuild')");
}

export function insertCards(db: Database, rows: CatalogCardInput[]): number {
  const stmt = db.prepare(`
    INSERT INTO cards (
      source, source_card_id, language, set_id, set_name, set_abbreviation,
      series_name, printed_total, card_number, card_number_norm, name,
      name_norm, english_name, english_name_norm, set_name_norm,
      set_abbreviation_norm
    ) VALUES (
      @source, @source_card_id, @language, @set_id, @set_name, @set_abbreviation,
      @series_name, @printed_total, @card_number, @card_number_norm, @name,
      @name_norm, @english_name, @english_name_norm, @set_name_norm,
      @set_abbreviation_norm
    )
    ON CONFLICT (source, language, source_card_id) DO UPDATE SET
      set_id = excluded.set_id,
      set_name = excluded.set_name,
      set_abbreviation = excluded.set_abbreviation,
      series_name = excluded.series_name,
      printed_total = excluded.printed_total,
      card_number = excluded.card_number,
      card_number_norm = excluded.card_number_norm,
      name = excluded.name,
      name_norm = excluded.name_norm,
      english_name = excluded.english_name,
      english_name_norm = excluded.english_name_norm,
      set_name_norm = excluded.set_name_norm,
      set_abbreviation_norm = excluded.set_abbreviation_norm
  `);

  const insertAll = db.transaction((batch: CatalogCardInput[]) => {
    for (const row of batch) {
      stmt.run({
        source: row.source,
        source_card_id: row.source_card_id,
        language: row.language,
        set_id: row.set_id,
        set_name: row.set_name,
        set_abbreviation: row.set_abbreviation ?? null,
        series_name: row.series_name ?? null,
        printed_total: row.printed_total ?? null,
        card_number: row.card_number,
        card_number_norm: normalizeNumber(row.card_number),
        name: row.name,
        name_norm: normalizeName(row.name),
        english_name: row.english_name ?? null,
        english_name_norm: row.english_name ? normalizeName(row.english_name) : null,
        set_name_norm: normalizeName(row.set_name),
        set_abbreviation_norm: row.set_abbreviation
          ? normalizeSetToken(row.set_abbreviation)
          : null,
      });
    }
  });

  insertAll(rows);
  return rows.length;
}

export function insertSets(db: Database, rows: Omit<CatalogSet, never>[]): number {
  const stmt = db.prepare(`
    INSERT INTO sets (
      source, language, set_id, set_name, local_name, set_abbreviation,
      series_name, release_date, printed_total, card_count_total,
      set_name_norm, set_abbreviation_norm
    ) VALUES (
      @source, @language, @set_id, @set_name, @local_name, @set_abbreviation,
      @series_name, @release_date, @printed_total, @card_count_total,
      @set_name_norm, @set_abbreviation_norm
    )
    ON CONFLICT (source, language, set_id) DO UPDATE SET
      set_name = excluded.set_name,
      local_name = excluded.local_name,
      set_abbreviation = excluded.set_abbreviation,
      series_name = excluded.series_name,
      release_date = excluded.release_date,
      printed_total = excluded.printed_total,
      card_count_total = excluded.card_count_total,
      set_name_norm = excluded.set_name_norm,
      set_abbreviation_norm = excluded.set_abbreviation_norm
  `);

  const insertAll = db.transaction((batch: typeof rows) => {
    for (const row of batch) {
      stmt.run({
        source: row.source,
        language: row.language,
        set_id: row.set_id,
        set_name: row.set_name,
        local_name: row.local_name ?? null,
        set_abbreviation: row.set_abbreviation ?? null,
        series_name: row.series_name ?? null,
        release_date: row.release_date ?? null,
        printed_total: row.printed_total ?? null,
        card_count_total: row.card_count_total ?? null,
        set_name_norm: normalizeName(row.set_name),
        set_abbreviation_norm: row.set_abbreviation
          ? normalizeSetToken(row.set_abbreviation)
          : null,
      });
    }
  });

  insertAll(rows);
  return rows.length;
}

/**
 * Fills in card fields from the richer `sets` rows.
 *
 * Some sources list only a set ID against each card (PikaQian sends a code like
 * "csve2c") while carrying the readable name on a separate sheet. Copying it
 * onto the card rows keeps lookups and result display to a single table.
 */
export function backfillFromSets(db: Database): number {
  const result = db
    .prepare(
      `UPDATE cards SET
         set_name = COALESCE(
           (SELECT s.set_name FROM sets s
            WHERE s.source = cards.source AND s.language = cards.language
              AND s.set_id = cards.set_id),
           cards.set_name),
         series_name = COALESCE(cards.series_name,
           (SELECT s.series_name FROM sets s
            WHERE s.source = cards.source AND s.language = cards.language
              AND s.set_id = cards.set_id)),
         printed_total = COALESCE(cards.printed_total,
           (SELECT s.printed_total FROM sets s
            WHERE s.source = cards.source AND s.language = cards.language
              AND s.set_id = cards.set_id))
       WHERE EXISTS (
         SELECT 1 FROM sets s
         WHERE s.source = cards.source AND s.language = cards.language
           AND s.set_id = cards.set_id
       )`
    )
    .run();

  db.prepare(
    `UPDATE cards SET set_name_norm = norm_name(set_name)
     WHERE set_name_norm != norm_name(set_name)`
  ).run();

  return result.changes;
}

export function getCard(db: Database, id: number): CatalogCard | undefined {
  return db
    .prepare(`SELECT ${CARD_COLUMNS} FROM cards WHERE id = ?`)
    .get(id) as CatalogCard | undefined;
}

export interface SearchFilters {
  /** Free-text: matched against card name, English name and set name. */
  q?: string;
  language?: string;
  /** Set ID, abbreviation or name. */
  set?: string;
  /** Collector number; normalized before comparison. */
  number?: string;
  source?: string;
  limit?: number;
  offset?: number;
}

export interface SearchResult {
  cards: CatalogCard[];
  total: number;
  limit: number;
  offset: number;
}

const MAX_LIMIT = 200;

/**
 * Paginated catalog search. Free text goes through the trigram index when it
 * is long enough, and falls back to a LIKE scan for one- and two-character
 * fragments, which the trigram index cannot serve.
 */
export function searchCards(db: Database, filters: SearchFilters = {}): SearchResult {
  const limit = Math.min(Math.max(filters.limit ?? 50, 1), MAX_LIMIT);
  const offset = Math.max(filters.offset ?? 0, 0);

  const clauses: string[] = [];
  const params: Record<string, unknown> = {};
  let from = "cards";

  const q = filters.q?.trim();
  if (q) {
    if (isTrigramSearchable(q)) {
      from = "cards JOIN cards_fts ON cards_fts.rowid = cards.id";
      clauses.push("cards_fts MATCH @fts");
      params.fts = ftsQuery(q);
    } else {
      clauses.push(
        "(cards.name LIKE @like OR cards.english_name LIKE @like OR cards.set_name LIKE @like)"
      );
      params.like = `%${q}%`;
    }
  }

  if (filters.language?.trim()) {
    clauses.push("cards.language = @language");
    params.language = filters.language.trim();
  }
  if (filters.source?.trim()) {
    clauses.push("cards.source = @source");
    params.source = filters.source.trim();
  }
  if (filters.set?.trim()) {
    const set = filters.set.trim();
    clauses.push(
      `(cards.set_id = @setExact OR cards.set_abbreviation_norm = @setNorm
        OR cards.set_name_norm = @setNorm)`
    );
    params.setExact = set;
    params.setNorm = normalizeSetToken(set);
  }
  if (filters.number?.trim()) {
    clauses.push("cards.card_number_norm = @number");
    params.number = normalizeNumber(filters.number);
  }

  const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";

  const total = (
    db.prepare(`SELECT COUNT(*) AS n FROM ${from} ${where}`).get(params) as {
      n: number;
    }
  ).n;

  const cards = db
    .prepare(
      `SELECT ${CARD_COLUMNS.split(",")
        .map((c) => `cards.${c.trim()}`)
        .join(", ")}
       FROM ${from} ${where}
       ORDER BY cards.language, cards.set_id, cards.card_number_norm
       LIMIT @limit OFFSET @offset`
    )
    .all({ ...params, limit, offset }) as CatalogCard[];

  return { cards, total, limit, offset };
}

/**
 * Escapes free text for an FTS5 MATCH. With the trigram tokenizer a quoted
 * string is a substring search, so the only thing to handle is embedded quotes.
 */
export function ftsQuery(text: string): string {
  return `"${text.replace(/"/g, '""')}"`;
}

export function listLanguages(
  db: Database
): { language: string; card_count: number }[] {
  return db
    .prepare(
      `SELECT language, COUNT(*) AS card_count
       FROM cards GROUP BY language ORDER BY card_count DESC`
    )
    .all() as { language: string; card_count: number }[];
}

export function listSets(
  db: Database,
  filters: { language?: string; q?: string; limit?: number } = {}
): CatalogSet[] {
  const clauses: string[] = [];
  const params: Record<string, unknown> = {
    limit: Math.min(Math.max(filters.limit ?? 500, 1), 2000),
  };

  if (filters.language?.trim()) {
    clauses.push("language = @language");
    params.language = filters.language.trim();
  }
  if (filters.q?.trim()) {
    clauses.push(
      `(set_name_norm LIKE @q OR set_abbreviation_norm LIKE @q OR set_id LIKE @qRaw)`
    );
    params.q = `%${normalizeName(filters.q)}%`;
    params.qRaw = `%${filters.q.trim()}%`;
  }

  const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
  return db
    .prepare(
      `SELECT source, language, set_id, set_name, local_name, set_abbreviation,
              series_name, release_date, printed_total, card_count_total
       FROM sets ${where}
       ORDER BY release_date DESC, set_name
       LIMIT @limit`
    )
    .all(params) as CatalogSet[];
}

export function countCards(db: Database): number {
  return (db.prepare("SELECT COUNT(*) AS n FROM cards").get() as { n: number }).n;
}
