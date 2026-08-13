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
  game: string;
  language: string;
  name: string;
  name_en: string | null;
  abbreviation: string | null;
  release_date: string;
  card_count_official: number | null;
  source_id: string | null;
}

const GAMES = [{ code: "pokemon", name: "Pokémon TCG", kind: "tcg" }];

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
  set("pokemon:en:bs", "pokemon", "en", "Base Set", "Base Set", "BS", "1999-01-09", 102, "base1"),
  // Same printed code as pokemon:en:bs, which is why "BS" alone cannot be decisive.
  set("pokemon:en:bs-1999", "pokemon", "en", "Base Set (Shadowless)", "Base Set (Shadowless)", "BS", "1999-01-09", null, null),
  set("pokemon:fr:bs", "pokemon", "fr", "Set de Base", null, "BS", "1999-01-09", 102, "base1"),
  set("pokemon:de:bs", "pokemon", "de", "Grundset", null, "BS", "1999-01-09", 102, "base1"),
  set("pokemon:en:b2", "pokemon", "en", "Base Set 2", "Base Set 2", "B2", "2000-02-24", 130, "base4"),
  set("pokemon:en:tr", "pokemon", "en", "Team Rocket", "Team Rocket", "TR", "2000-04-24", 82, "base5"),
  set("pokemon:ja:sv1a", "pokemon", "ja", "トリプレットビート", "Triplet Beat", "SV1a", "2023-03-10", 73, "SV1a"),
  set("pokemon:zh-cn:csve2c", "pokemon", "zh-cn", "对战派对 耀梦", "Battle Party: Shining Dream", "CSVE2C", "2024-05-01", null, null),
];

interface CardRow {
  set_uid: string;
  number: string;
  name: string;
  name_en: string | null;
  card_id: string | null;
}

const CARDS: CardRow[] = [
  { set_uid: "pokemon:en:bs", number: "4", name: "Charizard", name_en: null, card_id: "base1-4" },
  { set_uid: "pokemon:en:bs", number: "2", name: "Blastoise", name_en: null, card_id: "base1-2" },
  { set_uid: "pokemon:fr:bs", number: "4", name: "Dracaufeu", name_en: "Charizard", card_id: "base1-4" },
  { set_uid: "pokemon:fr:bs", number: "2", name: "Tortank", name_en: "Blastoise", card_id: "base1-2" },
  { set_uid: "pokemon:de:bs", number: "4", name: "Glurak", name_en: "Charizard", card_id: "base1-4" },
  { set_uid: "pokemon:en:b2", number: "4", name: "Charizard", name_en: null, card_id: "base4-4" },
  { set_uid: "pokemon:en:tr", number: "4", name: "Dark Charizard", name_en: null, card_id: "base5-4" },
  { set_uid: "pokemon:ja:sv1a", number: "001", name: "トロピウス", name_en: "Tropius", card_id: "SV1a-001" },
  { set_uid: "pokemon:ja:sv1a", number: "013", name: "メガリザードンXex", name_en: null, card_id: "SV1a-013" },
  { set_uid: "pokemon:zh-cn:csve2c", number: "001", name: "妙蛙种子", name_en: "Bulbasaur", card_id: "uuid-bulbasaur" },
];

export function buildTestCatalog(): Database.Database {
  const db = new Database(":memory:");
  db.exec(fs.readFileSync(SCHEMA_PATH, "utf8"));

  const insertGame = db.prepare(
    `INSERT INTO games (code, name, kind) VALUES (@code, @name, @kind)`
  );
  for (const game of GAMES) insertGame.run(game);

  const insertLanguage = db.prepare(
    `INSERT INTO languages (code, name_en, name_native, region)
     VALUES (@code, @name_en, @name_native, @region)`
  );
  for (const language of LANGUAGES) insertLanguage.run(language);

  const insertSet = db.prepare(
    `INSERT INTO sets (set_uid, game, language, name, name_en, abbreviation, release_date,
                       release_year, series_name, card_count_official, card_count_total,
                       card_count_loaded, sources, source_count)
     VALUES (@set_uid, @game, @language, @name, @name_en, @abbreviation, @release_date,
             @release_year, NULL, @card_count_official, @card_count_official,
             0, 'test', 1)`
  );
  const insertSourceId = db.prepare(
    `INSERT INTO set_source_ids (set_uid, source, source_id)
     VALUES (@set_uid, 'test', @source_id)`
  );
  for (const row of SETS) {
    insertSet.run({ ...row, release_year: Number(row.release_date.slice(0, 4)) });
    if (row.source_id) {
      insertSourceId.run({ set_uid: row.set_uid, source_id: row.source_id });
    }
  }

  const insertCard = db.prepare(
    `INSERT INTO cards (card_uid, set_uid, game, language, number, number_prefix, number_value,
                        name, name_en, name_en_source, card_id, sources)
     VALUES (@card_uid, @set_uid, @game, @language, @number, NULL, @number_value,
             @name, @name_en, @name_en_source, @card_id, 'test')`
  );
  for (const row of CARDS) {
    const setRow = SETS.find((s) => s.set_uid === row.set_uid)!;
    insertCard.run({
      ...row,
      card_uid: `${row.set_uid}#${row.number}`,
      game: setRow.game,
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
  game: string,
  language: string,
  name: string,
  name_en: string | null,
  abbreviation: string | null,
  release_date: string,
  card_count_official: number | null,
  source_id: string | null
): SetRow {
  return {
    set_uid,
    game,
    language,
    name,
    name_en,
    abbreviation,
    release_date,
    card_count_official,
    source_id,
  };
}
