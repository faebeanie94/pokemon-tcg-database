import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";
import { buildMatchIndex } from "../catalog";

/**
 * A miniature catalog in the real canonical shape.
 *
 * The schema is loaded from `src/pokedb/schema.sql`, the same file the Python
 * build applies, so these tests fail if the two sides drift apart rather than
 * passing against a hand-copied schema that no longer exists.
 *
 * The rows deliberately include the cases that make matching hard: one printing
 * in several languages, two sets sharing a collector number, two English sets
 * sharing the code "BS", a Japanese set code shaped like a card number, and
 * Chinese cards whose English name comes from a separate column.
 */

const SCHEMA_PATH = path.join(process.cwd(), "src", "pokedb", "schema.sql");

interface SetRow {
  set_uid: string;
  language: string;
  name: string;
  name_en: string | null;
  abbreviation: string | null;
  release_date: string;
  card_count_official: number | null;
  tcgdex_set_id: string | null;
}

const LANGUAGES = [
  { code: "en", name_en: "English", name_native: "English", region: "western" },
  { code: "fr", name_en: "French", name_native: "Français", region: "western" },
  { code: "de", name_en: "German", name_native: "Deutsch", region: "western" },
  { code: "ja", name_en: "Japanese", name_native: "日本語", region: "asian" },
  {
    code: "zh-cn",
    name_en: "Chinese (Simplified)",
    name_native: "简体中文",
    region: "asian",
  },
];

const SETS: SetRow[] = [
  set("en:bs", "en", "Base Set", "Base Set", "BS", "1999-01-09", 102, "base1"),
  // Same printed code as en:bs, which is why "BS" alone cannot be decisive.
  set("en:bs-1999", "en", "Base Set (Shadowless)", "Base Set (Shadowless)", "BS", "1999-01-09", null, null),
  set("fr:bs", "fr", "Set de Base", null, "BS", "1999-01-09", 102, "base1"),
  set("de:bs", "de", "Grundset", null, "BS", "1999-01-09", 102, "base1"),
  set("en:b2", "en", "Base Set 2", "Base Set 2", "B2", "2000-02-24", 130, "base4"),
  set("en:tr", "en", "Team Rocket", "Team Rocket", "TR", "2000-04-24", 82, "base5"),
  set("ja:sv1a", "ja", "トリプレットビート", "Triplet Beat", "SV1a", "2023-03-10", 73, "SV1a"),
  set("zh-cn:csve2c", "zh-cn", "对战派对 耀梦", "Battle Party: Shining Dream", "CSVE2C", "2024-05-01", null, null),
];

interface CardRow {
  set_uid: string;
  number: string;
  name: string;
  name_en: string | null;
  card_id: string | null;
}

const CARDS: CardRow[] = [
  { set_uid: "en:bs", number: "4", name: "Charizard", name_en: null, card_id: "base1-4" },
  { set_uid: "en:bs", number: "2", name: "Blastoise", name_en: null, card_id: "base1-2" },
  { set_uid: "fr:bs", number: "4", name: "Dracaufeu", name_en: "Charizard", card_id: "base1-4" },
  { set_uid: "fr:bs", number: "2", name: "Tortank", name_en: "Blastoise", card_id: "base1-2" },
  { set_uid: "de:bs", number: "4", name: "Glurak", name_en: "Charizard", card_id: "base1-4" },
  { set_uid: "en:b2", number: "4", name: "Charizard", name_en: null, card_id: "base4-4" },
  { set_uid: "en:tr", number: "4", name: "Dark Charizard", name_en: null, card_id: "base5-4" },
  { set_uid: "ja:sv1a", number: "001", name: "トロピウス", name_en: "Tropius", card_id: "SV1a-001" },
  { set_uid: "ja:sv1a", number: "013", name: "メガリザードンXex", name_en: null, card_id: "SV1a-013" },
  { set_uid: "zh-cn:csve2c", number: "001", name: "妙蛙种子", name_en: "Bulbasaur", card_id: "uuid-bulbasaur" },
];

export function buildTestCatalog(): Database.Database {
  const db = new Database(":memory:");
  db.exec(fs.readFileSync(SCHEMA_PATH, "utf8"));

  const insertLanguage = db.prepare(
    `INSERT INTO languages (code, name_en, name_native, region)
     VALUES (@code, @name_en, @name_native, @region)`
  );
  for (const language of LANGUAGES) insertLanguage.run(language);

  const insertSet = db.prepare(
    `INSERT INTO sets (set_uid, language, name, name_en, abbreviation, release_date,
                       release_year, series_name, card_count_official, card_count_total,
                       card_count_loaded, tcgdex_set_id, sources, source_count)
     VALUES (@set_uid, @language, @name, @name_en, @abbreviation, @release_date,
             @release_year, NULL, @card_count_official, @card_count_official,
             0, @tcgdex_set_id, 'test', 1)`
  );
  for (const row of SETS) {
    insertSet.run({ ...row, release_year: Number(row.release_date.slice(0, 4)) });
  }

  const insertCard = db.prepare(
    `INSERT INTO cards (card_uid, set_uid, language, number, number_prefix, number_value,
                        name, name_en, name_en_source, card_id, sources)
     VALUES (@card_uid, @set_uid, @language, @number, NULL, @number_value,
             @name, @name_en, @name_en_source, @card_id, 'test')`
  );
  for (const row of CARDS) {
    const setRow = SETS.find((s) => s.set_uid === row.set_uid)!;
    insertCard.run({
      ...row,
      card_uid: `${row.set_uid}#${row.number}`,
      language: setRow.language,
      number_value: Number(row.number),
      name_en_source: row.name_en ? "source" : null,
    });
  }

  db.exec(
    `UPDATE sets SET card_count_loaded =
       (SELECT COUNT(*) FROM cards WHERE cards.set_uid = sets.set_uid)`
  );
  db.prepare("INSERT INTO build_info (key, value) VALUES ('built_at', ?)").run(
    "2026-01-01T00:00:00Z"
  );

  buildMatchIndex(db);
  return db;
}

function set(
  set_uid: string,
  language: string,
  name: string,
  name_en: string | null,
  abbreviation: string | null,
  release_date: string,
  card_count_official: number | null,
  tcgdex_set_id: string | null
): SetRow {
  return {
    set_uid,
    language,
    name,
    name_en,
    abbreviation,
    release_date,
    card_count_official,
    tcgdex_set_id,
  };
}
