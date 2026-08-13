import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";
import { buildMatchIndex } from "../catalog";

/**
 * A miniature catalog in the real canonical shape.
 *
 * The schema is loaded from `src/pokedb/schema.sql`, the same file the Python
 * build applies. Rows cover Pokémon hard cases plus sports grading examples.
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
  manufacturer: string | null;
  sport: string | null;
  product_year: string | null;
  source_id: string | null;
}

const GAMES = [
  { code: "pokemon", name: "Pokémon TCG", kind: "tcg" },
  { code: "sports", name: "Sports & Entertainment Cards", kind: "sports" },
  { code: "mtg", name: "Magic: The Gathering", kind: "tcg" },
];

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
  set("pokemon:en:bs", "pokemon", "en", "Base Set", "Base Set", "BS", "1999-01-09", 102, null, null, null, "base1"),
  set("pokemon:en:bs-1999", "pokemon", "en", "Base Set (Shadowless)", "Base Set (Shadowless)", "BS", "1999-01-09", null, null, null, null, null),
  set("pokemon:fr:bs", "pokemon", "fr", "Set de Base", null, "BS", "1999-01-09", 102, null, null, null, "base1"),
  set("pokemon:de:bs", "pokemon", "de", "Grundset", null, "BS", "1999-01-09", 102, null, null, null, "base1"),
  set("pokemon:en:b2", "pokemon", "en", "Base Set 2", "Base Set 2", "B2", "2000-02-24", 130, null, null, null, "base4"),
  set("pokemon:en:tr", "pokemon", "en", "Team Rocket", "Team Rocket", "TR", "2000-04-24", 82, null, null, null, "base5"),
  set("pokemon:ja:sv1a", "pokemon", "ja", "トリプレットビート", "Triplet Beat", "SV1a", "2023-03-10", 73, null, null, null, "SV1a"),
  set("pokemon:zh-cn:csve2c", "pokemon", "zh-cn", "对战派对 耀梦", "Battle Party: Shining Dream", "CSVE2C", "2024-05-01", null, null, null, null, null),
  set(
    "sports:en:202526toppsmanchesterunitedteamset",
    "sports",
    "en",
    "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
    "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
    null,
    "2025-09-01",
    null,
    "Topps",
    "soccer",
    "2025-26",
    "2025-26-topps-manchester-united-team-set"
  ),
  set(
    "sports:en:2024paniniflawlesswwe",
    "sports",
    "en",
    "2024 PANINI FLAWLESS WWE",
    "2024 PANINI FLAWLESS WWE",
    null,
    "2024-11-15",
    null,
    "Panini",
    "wrestling",
    "2024",
    "2024-panini-flawless-wwe"
  ),
];

interface CardRow {
  set_uid: string;
  number: string;
  name: string;
  name_en: string | null;
  card_id: string | null;
  subject_name?: string | null;
  parallel?: string | null;
  notations?: string | null;
  serial_number?: string | null;
  print_run?: number | null;
  display_name?: string | null;
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
  {
    set_uid: "sports:en:202526toppsmanchesterunitedteamset",
    number: "38",
    name: "SIR DAVID BECKHAM",
    name_en: "SIR DAVID BECKHAM",
    card_id: null,
    subject_name: "SIR DAVID BECKHAM",
    display_name: "SIR DAVID BECKHAM",
  },
  {
    set_uid: "sports:en:202526toppsmanchesterunitedteamset",
    number: "38",
    name: "SIR DAVID BECKHAM - HALO REF.",
    name_en: "SIR DAVID BECKHAM - HALO REF.",
    card_id: null,
    subject_name: "SIR DAVID BECKHAM",
    parallel: "HALO REF",
    display_name: "SIR DAVID BECKHAM - HALO REF.",
  },
  {
    set_uid: "sports:en:2024paniniflawlesswwe",
    number: "SSL-SM",
    name: "SHAWN MICHAELS",
    name_en: "SHAWN MICHAELS",
    card_id: null,
    subject_name: "SHAWN MICHAELS",
    display_name: "SHAWN MICHAELS",
  },
  {
    set_uid: "sports:en:2024paniniflawlesswwe",
    number: "SSL-SM",
    name: "SHAWN MICHAELS – AUTO - RUBY REF. – 09/15",
    name_en: "SHAWN MICHAELS – AUTO - RUBY REF. – 09/15",
    card_id: null,
    subject_name: "SHAWN MICHAELS",
    parallel: "RUBY REF",
    notations: "AUTO",
    serial_number: "09",
    print_run: 15,
    display_name: "SHAWN MICHAELS - AUTO - RUBY REF - 09/15",
  },
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
                       card_count_loaded, manufacturer, sport, product_year, sources, source_count)
     VALUES (@set_uid, @game, @language, @name, @name_en, @abbreviation, @release_date,
             @release_year, NULL, @card_count_official, @card_count_official,
             0, @manufacturer, @sport, @product_year, 'test', 1)`
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
                        name, name_en, name_en_source, card_id, subject_name, parallel,
                        notations, serial_number, print_run, display_name, sources)
     VALUES (@card_uid, @set_uid, @game, @language, @number, @number_prefix, @number_value,
             @name, @name_en, @name_en_source, @card_id, @subject_name, @parallel,
             @notations, @serial_number, @print_run, @display_name, 'test')`
  );
  for (const row of CARDS) {
    const setRow = SETS.find((s) => s.set_uid === row.set_uid)!;
    const parallelSlug = row.parallel
      ? row.parallel.toLowerCase().replace(/[^a-z0-9]+/g, "")
      : "";
    const card_uid = parallelSlug
      ? `${row.set_uid}#${row.number}#${parallelSlug}`
      : `${row.set_uid}#${row.number}`;
    const numMatch = String(row.number).match(/^([A-Za-z]*)[\s-]*(\d+)/);
    insertCard.run({
      ...row,
      card_uid,
      game: setRow.game,
      language: setRow.language,
      number_prefix: numMatch?.[1] ? numMatch[1].toUpperCase() : null,
      number_value: numMatch?.[2] ? Number(numMatch[2]) : null,
      name_en_source: row.name_en ? "source" : null,
      subject_name: row.subject_name ?? null,
      parallel: row.parallel ?? null,
      notations: row.notations ?? null,
      serial_number: row.serial_number ?? null,
      print_run: row.print_run ?? null,
      display_name: row.display_name ?? row.name,
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
  manufacturer: string | null,
  sport: string | null,
  product_year: string | null,
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
    manufacturer,
    sport,
    product_year,
    source_id,
  };
}
