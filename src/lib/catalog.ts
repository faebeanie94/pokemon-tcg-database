import type { Database } from "better-sqlite3";
import {
  normalizeName,
  normalizeNumber,
  normalizeSetToken,
  normalizeSportsNumber,
} from "./normalize";
import { isTrigramSearchable } from "./query";

/**
 * Read layer over the canonical card database that `python -m pokedb build`
 * produces at `build/pokemon_tcg.sqlite`.
 *
 * That build is the single source of truth: it merges the curated set list, the
 * PikaQian workbook and the TCGdex API into `sets` and `cards`, and derives
 * English names for cards printed in Japanese, Chinese and Korean. Nothing here
 * writes to those tables.
 *
 * What this module does add is a *derived* match index in the same file
 * (`match_cards`, `match_sets`, `cards_fts`), holding the normalized comparison
 * keys and the full-text index that matching needs. It lives beside the
 * canonical tables rather than in a second database so there is one file to
 * build, back up and ship — and it is rebuilt from them, never edited by hand.
 */

export interface CatalogCard {
  /** Stable canonical identifier, '<game>:<language>:<set>#<number>[#parallel]'. */
  card_uid: string;
  set_uid: string;
  game: string;
  language: string;
  set_name: string;
  set_name_en: string | null;
  /** Set code as printed, e.g. 'BS' or 'CSVE2C'. */
  set_code: string | null;
  series_name: string | null;
  manufacturer: string | null;
  sport: string | null;
  product_year?: string | null;
  /** The denominator printed on the card: the 102 in '4/102'. */
  printed_total: number | null;
  card_number: string;
  name: string;
  english_name: string | null;
  subject_name: string | null;
  parallel: string | null;
  notations: string | null;
  serial_number: string | null;
  print_run: number | null;
  display_name: string | null;
  /** Identifier from the source that supplied the card, e.g. 'base1-4'. */
  card_id: string | null;
  sources: string;
}

export interface CatalogSet {
  set_uid: string;
  game: string;
  language: string;
  set_name: string;
  set_name_en: string | null;
  set_code: string | null;
  series_name: string | null;
  manufacturer: string | null;
  sport: string | null;
  product_year: string | null;
  release_date: string | null;
  printed_total: number | null;
  card_count_total: number | null;
  cards_loaded: number;
}

/**
 * English printings carry no separate English name because their name already
 * is one; coalescing here means a query for an English name matches every
 * language uniformly.
 */
const CARD_FIELDS = `
  c.card_uid, c.set_uid, c.game, c.language,
  s.name AS set_name, s.name_en AS set_name_en, s.abbreviation AS set_code,
  s.series_name, s.manufacturer, s.sport, s.product_year,
  s.card_count_official AS printed_total,
  c.number AS card_number, c.name,
  COALESCE(c.name_en, CASE WHEN c.language = 'en' THEN c.name END) AS english_name,
  c.subject_name, c.parallel, c.notations, c.serial_number, c.print_run,
  c.display_name, c.card_id, c.sources`;

const FROM_CARDS = "cards c JOIN sets s ON s.set_uid = c.set_uid";

/** Printed numbers sort naturally with the prefix/value columns the build derives. */
const CARD_ORDER =
  "s.game, s.language, s.name, COALESCE(c.number_prefix, ''), COALESCE(c.number_value, 999999)";

/**
 * Exposes the app's normalizers to SQL so the index is built with the same code
 * the query path compares against, rather than an approximation of it.
 */
export function registerSqlFunctions(db: Database): void {
  db.function("norm_name", { deterministic: true }, (value: unknown) =>
    normalizeName(value == null ? "" : String(value))
  );
  db.function("norm_number", { deterministic: true }, (value: unknown) =>
    normalizeNumber(value == null ? "" : String(value))
  );
  db.function("norm_sports_number", { deterministic: true }, (value: unknown) =>
    normalizeSportsNumber(value == null ? "" : String(value))
  );
}

export class CatalogNotBuiltError extends Error {}

/** True when the canonical tables exist, i.e. a pokedb build has run. */
export function isCatalogBuilt(db: Database): boolean {
  const row = db
    .prepare(
      `SELECT COUNT(*) AS n FROM sqlite_master
       WHERE type = 'table' AND name IN ('cards', 'sets')`
    )
    .get() as { n: number };
  return row.n === 2;
}

export function requireCatalog(db: Database): void {
  if (!isCatalogBuilt(db)) {
    throw new CatalogNotBuiltError(
      "no card data in this database yet; run `python -m pokedb update` to build it"
    );
  }
}

/** The `built_at` stamp of the canonical build, or null if there is none. */
export function canonicalBuiltAt(db: Database): string | null {
  if (!isCatalogBuilt(db)) return null;
  const row = db
    .prepare("SELECT value FROM build_info WHERE key = 'built_at'")
    .get() as { value: string } | undefined;
  return row?.value ?? null;
}

function indexBuiltFor(db: Database): string | null {
  const exists = db
    .prepare(
      `SELECT COUNT(*) AS n FROM sqlite_master
       WHERE type = 'table' AND name = 'match_index_info'`
    )
    .get() as { n: number };
  if (!exists.n) return null;
  const row = db
    .prepare("SELECT value FROM match_index_info WHERE key = 'built_for'")
    .get() as { value: string } | undefined;
  return row?.value ?? null;
}

/**
 * True when the match index is missing, or was built from an older version of
 * the canonical data. The API's refresh swaps in a freshly built file, so this
 * has to be checked rather than assumed.
 */
export function isIndexStale(db: Database): boolean {
  const canonical = canonicalBuiltAt(db);
  if (!canonical) return false;
  return indexBuiltFor(db) !== canonical;
}

export interface IndexStats {
  cards: number;
  setTokens: number;
  builtFor: string | null;
}

/**
 * Rebuilds the derived match index from the canonical tables. Cheap enough
 * (a few seconds for ~145k cards) to redo wholesale rather than update in place.
 */
export function buildMatchIndex(db: Database): IndexStats {
  requireCatalog(db);
  registerSqlFunctions(db);

  db.exec(`
    DROP TABLE IF EXISTS match_cards;
    DROP TABLE IF EXISTS match_sets;
    DROP TABLE IF EXISTS cards_fts;
    DROP TABLE IF EXISTS match_index_info;

    -- Normalized comparison keys, so padded and unpadded numbers and accented
    -- and plain spellings compare equal.
    CREATE TABLE match_cards (
      card_uid       TEXT PRIMARY KEY,
      game           TEXT NOT NULL,
      name_norm      TEXT NOT NULL,
      name_en_norm   TEXT,
      subject_norm   TEXT,
      parallel_norm  TEXT,
      display_norm        TEXT,
      number_norm         TEXT NOT NULL,
      sports_number_norm  TEXT NOT NULL
    );

    -- Every way a set can be referred to: printed code, canonical UID, the
    -- source identifiers, and the local and English names. One row per token,
    -- which is what lets "BS", "base1" and "Base Set" all resolve.
    CREATE TABLE match_sets (
      set_uid    TEXT NOT NULL,
      game       TEXT NOT NULL,
      token_norm TEXT NOT NULL,
      kind       TEXT NOT NULL,
      PRIMARY KEY (set_uid, token_norm)
    );

    CREATE TABLE match_index_info (key TEXT PRIMARY KEY, value TEXT);

    -- Substring search over names in any script. The trigram tokenizer is what
    -- makes partial Japanese and Chinese names findable; a word tokenizer
    -- cannot split CJK text.
    CREATE VIRTUAL TABLE cards_fts USING fts5(
      card_uid UNINDEXED, name, name_en, subject_name, display_name, set_name,
      tokenize='trigram'
    );
  `);

  db.exec(`
    INSERT INTO match_cards (
      card_uid, game, name_norm, name_en_norm, subject_norm, parallel_norm,
      display_norm, number_norm, sports_number_norm
    )
    SELECT c.card_uid,
           c.game,
           norm_name(c.name),
           CASE
             WHEN c.name_en IS NOT NULL THEN norm_name(c.name_en)
             WHEN c.language = 'en' THEN norm_name(c.name)
           END,
           norm_name(c.subject_name),
           norm_name(c.parallel),
           norm_name(COALESCE(c.display_name, c.name)),
           norm_number(c.number),
           norm_sports_number(c.number)
      FROM cards c;

    INSERT OR IGNORE INTO match_sets (set_uid, game, token_norm, kind)
    SELECT set_uid, game, token_norm, kind FROM (
      SELECT set_uid, game, norm_name(abbreviation)  AS token_norm, 'code' AS kind FROM sets
      UNION ALL
      SELECT set_uid, game, norm_name(name),                        'name'          FROM sets
      UNION ALL
      SELECT set_uid, game, norm_name(name_en),                     'name_en'       FROM sets
      UNION ALL
      SELECT set_uid, game, norm_name(manufacturer),                'manufacturer'  FROM sets
      UNION ALL
      SELECT s.set_uid, s.game, norm_name(i.source_id),             'source_id'
        FROM sets s JOIN set_source_ids i ON i.set_uid = s.set_uid
      UNION ALL
      SELECT s.set_uid, s.game, norm_name(ss.source_set_id),        'source_id'
        FROM sets s JOIN set_sources ss ON ss.set_uid = s.set_uid
      UNION ALL
      SELECT set_uid, game, norm_name(set_uid),                     'uid'           FROM sets
      UNION ALL
      -- set_uid is '<game>:<language>:<code>'; expose the trailing code alone.
      SELECT set_uid, game, norm_name(
               CASE
                 WHEN instr(substr(set_uid, instr(set_uid, ':') + 1), ':') > 0
                 THEN substr(
                        substr(set_uid, instr(set_uid, ':') + 1),
                        instr(substr(set_uid, instr(set_uid, ':') + 1), ':') + 1
                      )
                 ELSE substr(set_uid, instr(set_uid, ':') + 1)
               END
             ), 'code'
        FROM sets
    ) WHERE token_norm IS NOT NULL AND token_norm != '';

    CREATE INDEX idx_match_cards_name     ON match_cards (name_norm);
    CREATE INDEX idx_match_cards_name_en  ON match_cards (name_en_norm);
    CREATE INDEX idx_match_cards_subject  ON match_cards (subject_norm);
    CREATE INDEX idx_match_cards_parallel ON match_cards (parallel_norm);
    CREATE INDEX idx_match_cards_number   ON match_cards (number_norm);
    CREATE INDEX idx_match_cards_snumber  ON match_cards (sports_number_norm);
    CREATE INDEX idx_match_cards_game     ON match_cards (game);
    CREATE INDEX idx_match_sets_token     ON match_sets (token_norm);
    CREATE INDEX idx_match_sets_game      ON match_sets (game);

    INSERT INTO cards_fts (card_uid, name, name_en, subject_name, display_name, set_name)
    SELECT c.card_uid, c.name, c.name_en, c.subject_name, c.display_name, s.name
      FROM cards c JOIN sets s ON s.set_uid = c.set_uid;
  `);

  const builtFor = canonicalBuiltAt(db);
  db.prepare(
    "INSERT OR REPLACE INTO match_index_info (key, value) VALUES ('built_for', ?)"
  ).run(builtFor);
  db.prepare(
    "INSERT OR REPLACE INTO match_index_info (key, value) VALUES ('built_at', ?)"
  ).run(new Date().toISOString());

  return {
    cards: (db.prepare("SELECT COUNT(*) AS n FROM match_cards").get() as { n: number })
      .n,
    setTokens: (
      db.prepare("SELECT COUNT(*) AS n FROM match_sets").get() as { n: number }
    ).n,
    builtFor,
  };
}

export function getCard(db: Database, cardUid: string): CatalogCard | undefined {
  return db
    .prepare(`SELECT ${CARD_FIELDS} FROM ${FROM_CARDS} WHERE c.card_uid = ?`)
    .get(cardUid) as CatalogCard | undefined;
}

export interface SearchFilters {
  /** Free text, matched against card name, English name and set name. */
  q?: string;
  game?: string;
  language?: string;
  /** Set code, canonical UID, source ID or name. */
  set?: string;
  /** Collector number; normalized before comparison. */
  number?: string;
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
 * Paginated catalog search. Free text goes through the trigram index when it is
 * long enough, and falls back to a scan for one- and two-character fragments,
 * which the trigram index cannot serve.
 */
export function searchCards(db: Database, filters: SearchFilters = {}): SearchResult {
  requireCatalog(db);
  const limit = Math.min(Math.max(filters.limit ?? 50, 1), MAX_LIMIT);
  const offset = Math.max(filters.offset ?? 0, 0);

  const clauses: string[] = [];
  const params: Record<string, unknown> = {};
  const joins: string[] = [];

  const q = filters.q?.trim();
  if (q) {
    if (isTrigramSearchable(q)) {
      joins.push("JOIN cards_fts ON cards_fts.card_uid = c.card_uid");
      clauses.push("cards_fts MATCH @fts");
      params.fts = ftsQuery(q);
    } else {
      clauses.push(
        "(c.name LIKE @like OR c.name_en LIKE @like OR s.name LIKE @like)"
      );
      params.like = `%${q}%`;
    }
  }

  if (filters.language?.trim()) {
    clauses.push("c.language = @language");
    params.language = filters.language.trim();
  }
  if (filters.game?.trim()) {
    clauses.push("c.game = @game");
    params.game = filters.game.trim();
  }
  if (filters.set?.trim()) {
    clauses.push(
      `c.set_uid IN (SELECT set_uid FROM match_sets WHERE token_norm = @setToken)`
    );
    params.setToken = normalizeSetToken(filters.set);
  }
  if (filters.number?.trim()) {
    joins.push("JOIN match_cards mc ON mc.card_uid = c.card_uid");
    clauses.push("(mc.number_norm = @number OR mc.sports_number_norm = @snumber)");
    params.number = normalizeNumber(filters.number);
    params.snumber = normalizeSportsNumber(filters.number);
  }

  const from = `${FROM_CARDS} ${joins.join(" ")}`;
  const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";

  const total = (
    db.prepare(`SELECT COUNT(*) AS n FROM ${from} ${where}`).get(params) as {
      n: number;
    }
  ).n;

  const cards = db
    .prepare(
      `SELECT ${CARD_FIELDS} FROM ${from} ${where}
       ORDER BY ${CARD_ORDER} LIMIT @limit OFFSET @offset`
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
  requireCatalog(db);
  return db
    .prepare(
      `SELECT language, COUNT(*) AS card_count
       FROM cards GROUP BY language ORDER BY card_count DESC`
    )
    .all() as { language: string; card_count: number }[];
}

export function listSets(
  db: Database,
  filters: { language?: string; game?: string; q?: string; limit?: number } = {}
): CatalogSet[] {
  requireCatalog(db);
  const clauses: string[] = [];
  const params: Record<string, unknown> = {
    limit: Math.min(Math.max(filters.limit ?? 500, 1), 2000),
  };

  if (filters.language?.trim()) {
    clauses.push("language = @language");
    params.language = filters.language.trim();
  }
  if (filters.game?.trim()) {
    clauses.push("game = @game");
    params.game = filters.game.trim();
  }
  if (filters.q?.trim()) {
    clauses.push(
      `(name LIKE @like OR name_en LIKE @like OR abbreviation LIKE @like
        OR set_uid LIKE @like OR manufacturer LIKE @like)`
    );
    params.like = `%${filters.q.trim()}%`;
  }

  const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
  return db
    .prepare(
      `SELECT set_uid, game, language, name AS set_name, name_en AS set_name_en,
              abbreviation AS set_code, series_name, manufacturer, sport,
              product_year, release_date,
              card_count_official AS printed_total, card_count_total,
              card_count_loaded AS cards_loaded
       FROM sets ${where}
       ORDER BY COALESCE(release_date, '9999') DESC, name
       LIMIT @limit`
    )
    .all(params) as CatalogSet[];
}

export function listGames(
  db: Database
): { game: string; name: string; kind: string; card_count: number }[] {
  requireCatalog(db);
  return db
    .prepare(
      `SELECT g.code AS game, g.name, g.kind,
              COALESCE(COUNT(c.card_uid), 0) AS card_count
         FROM games g
         LEFT JOIN cards c ON c.game = g.code
        GROUP BY g.code, g.name, g.kind
        ORDER BY card_count DESC, g.name`
    )
    .all() as { game: string; name: string; kind: string; card_count: number }[];
}

export function countCards(db: Database): number {
  requireCatalog(db);
  return (db.prepare("SELECT COUNT(*) AS n FROM cards").get() as { n: number }).n;
}
