import Database from "better-sqlite3";
import { insertSetAliases } from "../aliases";
import {
  backfillFromSets,
  initSchema,
  insertCards,
  insertSets,
  rebuildSearchIndex,
  type CatalogCardInput,
  type CatalogSet,
} from "../catalog";

/**
 * A miniature catalog with the shapes that make real matching hard:
 * the same printing in several languages, two sets sharing a collector
 * number, a Japanese set whose code looks like a card number, and Chinese
 * cards whose English name lives in a separate column.
 */

const SETS: CatalogSet[] = [
  set("en", "base1", "Base Set", "BS", 102, "1999-01-09"),
  set("fr", "base1", "Set de Base", "BS", 102, "1999-01-09"),
  set("de", "base1", "Grundset", "BS", 102, "1999-01-09"),
  set("en", "base4", "Base Set 2", "B2", 130, "2000-02-24"),
  set("en", "base5", "Team Rocket", "TR", 82, "2000-04-24"),
  set("ja", "SV1a", "トリプレットビート", null, 73, "2023-03-10"),
  set("zh-cn", "csve2c", "Gem Pack Volume 2", "csve2c", null, "2024-05-01"),
];

const CARDS: CatalogCardInput[] = [
  card("en", "base1", "4", "Charizard", null, 102),
  card("en", "base1", "2", "Blastoise", null, 102),
  card("fr", "base1", "4", "Dracaufeu", "Charizard", 102),
  card("fr", "base1", "2", "Tortank", "Blastoise", 102),
  card("de", "base1", "4", "Glurak", "Charizard", 102),
  card("en", "base4", "4", "Charizard", null, 130),
  card("en", "base5", "4", "Dark Charizard", null, 82),
  card("ja", "SV1a", "001", "トロピウス", null, 73),
  card("ja", "SV1a", "013", "メガリザードンXex", null, 73),
  card("zh-cn", "csve2c", "001", "妙蛙种子", "Bulbasaur", null),
];

export function buildTestCatalog(): Database.Database {
  const db = new Database(":memory:");
  initSchema(db);
  insertSets(db, SETS);
  insertCards(db, CARDS);
  insertSetAliases(db, [
    { language: "ja", set_id: "SV1a", alias: "Triplet Beat", source: "curated" },
    { language: "zh-cn", set_id: "csve2c", alias: "CSVE2C", source: "curated" },
  ]);
  backfillFromSets(db);
  rebuildSearchIndex(db);
  return db;
}

function set(
  language: string,
  set_id: string,
  set_name: string,
  set_abbreviation: string | null,
  printed_total: number | null,
  release_date: string
): CatalogSet {
  return {
    source: "tcgdex",
    language,
    set_id,
    set_name,
    local_name: null,
    set_abbreviation,
    series_name: null,
    release_date,
    printed_total,
    card_count_total: printed_total,
  };
}

function card(
  language: string,
  set_id: string,
  card_number: string,
  name: string,
  english_name: string | null,
  printed_total: number | null
): CatalogCardInput {
  const setRow = SETS.find((s) => s.language === language && s.set_id === set_id)!;
  return {
    source: "tcgdex",
    source_card_id: `${set_id}-${card_number}`,
    language,
    set_id,
    set_name: setRow.set_name,
    set_abbreviation: setRow.set_abbreviation,
    series_name: null,
    printed_total,
    card_number,
    name,
    english_name,
  };
}
