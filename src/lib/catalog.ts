import type { Database } from "better-sqlite3";
import { normalizeName, normalizeNumber, normalizeSetToken, normalizeSportsNumber } from "./normalize";
import { isTrigramSearchable } from "./query";

/**
 * Read layer over the canonical card database that `python -m pokedb build`
 * produces at `build/pokemon_tcg.sqlite`.
 *
 * That build is the single source of truth: it merges curated lists, API dumps
 * and sports seeds into `sets` and `cards`. Nothing here writes to those tables.
 *
 * What this module does add is a *derived* match index in the same file
 * (`match_cards`, `match_sets`, `cards_fts`), holding the normalized comparison
 * keys and the full-text index that matching needs.
 */

export interface CatalogCard {
  /** Stable canonical identifier, '<game>:<language>:<set>#<number>[#parallel]'. */
  card_uid: string;
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

const CARD_ORDER =
  "s.game, s.language, s.name, COALESCE(c.number_prefix, ''), COALESCE(c.number_value, 999999), COALESCE(c.parallel, '')";

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

export function isCatalogBuilt(db: Database): boolean {
  const row = db
    .prepare(
      `SELECT COUNT(*) AS n FROM sqlite_master
       WHERE type = 'table' AND name IN ('cards', 'sets', 'games')`
    )
    .get() as { n: number };
  return row.n === 3;
}

export function requireCatalog(db: Database): void {
  if (!isCatalogBuilt(db)) {
    throw new CatalogNotBuiltError(
      "no card data in this database yet; run `python -m pokedb update` to build it"
    );
  }
}

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

export function buildMatchIndex(db: Database): IndexStats {
  requireCatalog(db);
  registerSqlFunctions(db);

  db.exec(`
    DROP TABLE IF EXISTS match_cards;
    DROP TABLE IF EXISTS match_sets;
    DROP TABLE IF EXISTS cards_fts;
    DROP TABLE IF EXISTS match_index_info;

    CREATE TABLE match_cards (
      card_uid          TEXT PRIMARY KEY,
      game              TEXT NOT NULL,
      name_norm         TEXT NOT NULL,
      name_en_norm      TEXT,
      display_norm      TEXT,
      subject_norm      TEXT,
      parallel_norm     TEXT,
      number_norm       TEXT NOT NULL,
      sports_number_norm TEXT NOT NULL
    );

    CREATE TABLE match_sets (
      set_uid    TEXT NOT NULL,
      token_norm TEXT NOT NULL,
      kind       TEXT NOT NULL,
      game       TEXT NOT NULL,
      PRIMARY KEY (set_uid, token_norm)
    );

    CREATE TABLE match_index_info (key TEXT PRIMARY KEY, value TEXT);

    CREATE VIRTUAL TABLE cards_fts USING fts5(
      card_uid UNINDEXED, name, name_en, display_name, subject_name, parallel,
      set_name, tokenize='trigram'
    );
  `);

  db.exec(`
    INSERT INTO match_cards (
      card_uid, game, name_norm, name_en_norm, display_norm, subject_norm,
      parallel_norm, number_norm, sports_number_norm
    )
    SELECT c.card_uid,
           c.game,
           norm_name(c.name),
           CASE
             WHEN c.name_en IS NOT NULL THEN norm_name(c.name_en)
             WHEN c.language = 'en' THEN norm_name(c.name)
           END,
           norm_name(COALESCE(c.display_name, c.name)),
           norm_name(c.subject_name),
           norm_name(c.parallel),
           norm_number(c.number),
           norm_sports_number(c.number)
      FROM cards c;

    INSERT OR IGNORE INTO match_sets (set_uid, token_norm, kind, game)
    SELECT set_uid, token_norm, kind, game FROM (
      SELECT set_uid, game, norm_name(abbreviation) AS token_norm, 'code' AS kind FROM sets
      UNION ALL
      SELECT set_uid, game, norm_name(name), 'name' FROM sets
      UNION ALL
      SELECT set_uid, game, norm_name(name_en), 'name_en' FROM sets
      UNION ALL
      SELECT set_uid, game, norm_name(manufacturer), 'manufacturer' FROM sets
      UNION ALL
      SELECT set_uid, game, norm_name(set_uid), 'uid' FROM sets
      UNION ALL
      SELECT s.set_uid, s.game, norm_name(ssi.source_id), 'source_id'
        FROM sets s JOIN set_source_ids ssi ON ssi.set_uid = s.set_uid
      UNION ALL
      -- set_uid is '<game>:<language>:<code>'; the trailing code alone is useful.
      SELECT set_uid, game,
             norm_name(substr(set_uid, length(game) + length(language) + 3)),
             'code'
        FROM sets
    ) WHERE token_norm IS NOT NULL AND token_norm != '';

    CREATE INDEX idx_match_cards_name    ON match_cards (name_norm);
    CREATE INDEX idx_match_cards_name_en ON match_cards (name_en_norm);
    CREATE INDEX idx_match_cards_display ON match_cards (display_norm);
    CREATE INDEX idx_match_cards_subject ON match_cards (subject_norm);
    CREATE INDEX idx_match_cards_parallel ON match_cards (parallel_norm);
    CREATE INDEX idx_match_cards_number  ON match_cards (number_norm);
    CREATE INDEX idx_match_cards_snumber ON match_cards (sports_number_norm);
    CREATE INDEX idx_match_cards_game    ON match_cards (game);
    CREATE INDEX idx_match_sets_token    ON match_sets (token_norm);
    CREATE INDEX idx_match_sets_game     ON match_sets (game);

    INSERT INTO cards_fts (card_uid, name, name_en, display_name, subject_name, parallel, set_name)
    SELECT c.card_uid, c.name, c.name_en, c.display_name, c.subject_name, c.parallel, s.name
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
    cards: (db.prepare("SELECT COUNT(*) AS n FROM match_cards").get() as { n: number }).n,
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
  q?: string;
  game?: string;
  language?: string;
  set?: string;
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
        `(c.name LIKE @like OR c.name_en LIKE @like OR c.display_name LIKE @like
          OR c.subject_name LIKE @like OR s.name LIKE @like)`
      );
      params.like = `%${q}%`;
    }
  }

  if (filters.game?.trim()) {
    clauses.push("c.game = @game");
    params.game = filters.game.trim();
  }
  if (filters.language?.trim()) {
    clauses.push("c.language = @language");
    params.language = filters.language.trim();
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

export function listGames(db: Database): { game: string; name: string; kind: string; card_count: number }[] {
  requireCatalog(db);
  return db
    .prepare(
      `SELECT g.code AS game, g.name, g.kind, COUNT(c.card_uid) AS card_count
         FROM games g
         LEFT JOIN cards c ON c.game = g.code
        GROUP BY g.code
        HAVING card_count > 0
        ORDER BY card_count DESC`
    )
    .all() as { game: string; name: string; kind: string; card_count: number }[];
}

export function listSets(
  db: Database,
  filters: { game?: string; language?: string; q?: string; limit?: number } = {}
): CatalogSet[] {
  requireCatalog(db);
  const clauses: string[] = [];
  const params: Record<string, unknown> = {
    limit: Math.min(Math.max(filters.limit ?? 500, 1), 2000),
  };

  if (filters.game?.trim()) {
    clauses.push("game = @game");
    params.game = filters.game.trim();
  }
  if (filters.language?.trim()) {
    clauses.push("language = @language");
    params.language = filters.language.trim();
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
              abbreviation AS set_code, series_name, manufacturer, sport, product_year,
              release_date, card_count_official AS printed_total, card_count_total,
              card_count_loaded AS cards_loaded
       FROM sets ${where}
       ORDER BY COALESCE(release_date, '9999') DESC, name
       LIMIT @limit`
    )
    .all(params) as CatalogSet[];
}

export function countCards(db: Database): number {
  requireCatalog(db);
  return (db.prepare("SELECT COUNT(*) AS n FROM cards").get() as { n: number }).n;
}
