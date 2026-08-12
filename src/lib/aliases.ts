import type { Database } from "better-sqlite3";
import { normalizeSetToken } from "./normalize";

/**
 * Extra names a set is known by, beyond what the card sources provide.
 *
 * Graders identify sets by the abbreviation printed on the card or used in
 * house ("BS", "CSM1cC"), and TCGdex only supplies abbreviations for the
 * Western languages — Japanese, Korean, Chinese, Indonesian and Thai sets have
 * none. The curated workbook fills that gap, and English set names are
 * registered as aliases for non-English sets so an operator can look up a
 * Japanese card by the English set name.
 */
export interface SetAlias {
  language: string;
  set_id: string;
  alias: string;
  source: string;
}

export function initAliasSchema(db: Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS set_aliases (
      language TEXT NOT NULL,
      set_id TEXT NOT NULL,
      alias TEXT NOT NULL,
      alias_norm TEXT NOT NULL,
      source TEXT NOT NULL,
      PRIMARY KEY (language, set_id, alias_norm)
    );

    CREATE INDEX IF NOT EXISTS idx_set_aliases_norm ON set_aliases (alias_norm);
  `);
}

export function insertSetAliases(db: Database, rows: SetAlias[]): number {
  const stmt = db.prepare(
    `INSERT INTO set_aliases (language, set_id, alias, alias_norm, source)
     VALUES (@language, @set_id, @alias, @alias_norm, @source)
     ON CONFLICT (language, set_id, alias_norm) DO UPDATE SET
       alias = excluded.alias, source = excluded.source`
  );

  let written = 0;
  const insertAll = db.transaction((batch: SetAlias[]) => {
    for (const row of batch) {
      const alias_norm = normalizeSetToken(row.alias);
      if (!alias_norm) continue;
      stmt.run({ ...row, alias_norm });
      written += 1;
    }
  });

  insertAll(rows);
  return written;
}

export function countAliases(db: Database): number {
  return (db.prepare("SELECT COUNT(*) AS n FROM set_aliases").get() as { n: number })
    .n;
}
