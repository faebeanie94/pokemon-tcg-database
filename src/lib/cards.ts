import type { Database } from "better-sqlite3";

export interface Card {
  id: number;
  name: string;
  set: string;
  type: string;
  rarity: string;
  hp: number | null;
  created_at: string;
}

export interface NewCard {
  name: string;
  set: string;
  type: string;
  rarity: string;
  hp?: number | null;
}

export const CARD_TYPES = [
  "Grass",
  "Fire",
  "Water",
  "Lightning",
  "Psychic",
  "Fighting",
  "Darkness",
  "Metal",
  "Dragon",
  "Fairy",
  "Colorless",
] as const;

export const RARITIES = [
  "Common",
  "Uncommon",
  "Rare",
  "Rare Holo",
  "Ultra Rare",
  "Secret Rare",
] as const;

export function initSchema(db: Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS cards (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      "set" TEXT NOT NULL,
      type TEXT NOT NULL,
      rarity TEXT NOT NULL,
      hp INTEGER,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);
}

export interface CardFilters {
  search?: string;
  type?: string;
}

export function listCards(db: Database, filters: CardFilters = {}): Card[] {
  const clauses: string[] = [];
  const params: Record<string, unknown> = {};

  if (filters.search && filters.search.trim()) {
    clauses.push("(name LIKE @search OR \"set\" LIKE @search)");
    params.search = `%${filters.search.trim()}%`;
  }
  if (filters.type && filters.type.trim()) {
    clauses.push("type = @type");
    params.type = filters.type.trim();
  }

  const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
  const stmt = db.prepare(
    `SELECT id, name, "set", type, rarity, hp, created_at
     FROM cards ${where}
     ORDER BY id DESC`
  );
  return stmt.all(params) as Card[];
}

export function getCard(db: Database, id: number): Card | undefined {
  const stmt = db.prepare(
    `SELECT id, name, "set", type, rarity, hp, created_at FROM cards WHERE id = ?`
  );
  return stmt.get(id) as Card | undefined;
}

export class ValidationError extends Error {}

export function createCard(db: Database, input: NewCard): Card {
  const name = (input.name ?? "").trim();
  const set = (input.set ?? "").trim();
  const type = (input.type ?? "").trim();
  const rarity = (input.rarity ?? "").trim();

  if (!name) throw new ValidationError("name is required");
  if (!set) throw new ValidationError("set is required");
  if (!CARD_TYPES.includes(type as (typeof CARD_TYPES)[number])) {
    throw new ValidationError(`type must be one of: ${CARD_TYPES.join(", ")}`);
  }
  if (!RARITIES.includes(rarity as (typeof RARITIES)[number])) {
    throw new ValidationError(`rarity must be one of: ${RARITIES.join(", ")}`);
  }

  let hp: number | null = null;
  if (input.hp !== undefined && input.hp !== null && `${input.hp}` !== "") {
    const parsed = Number(input.hp);
    if (!Number.isFinite(parsed) || parsed < 0) {
      throw new ValidationError("hp must be a non-negative number");
    }
    hp = Math.round(parsed);
  }

  const stmt = db.prepare(
    `INSERT INTO cards (name, "set", type, rarity, hp) VALUES (?, ?, ?, ?, ?)`
  );
  const result = stmt.run(name, set, type, rarity, hp);
  return getCard(db, Number(result.lastInsertRowid))!;
}

export const SEED_CARDS: NewCard[] = [
  { name: "Charizard", set: "Base Set", type: "Fire", rarity: "Rare Holo", hp: 120 },
  { name: "Blastoise", set: "Base Set", type: "Water", rarity: "Rare Holo", hp: 100 },
  { name: "Venusaur", set: "Base Set", type: "Grass", rarity: "Rare Holo", hp: 100 },
  { name: "Pikachu", set: "Base Set", type: "Lightning", rarity: "Common", hp: 40 },
  { name: "Mewtwo", set: "Base Set", type: "Psychic", rarity: "Rare Holo", hp: 60 },
  { name: "Gyarados", set: "Base Set", type: "Water", rarity: "Rare Holo", hp: 100 },
  { name: "Alakazam", set: "Base Set", type: "Psychic", rarity: "Rare Holo", hp: 80 },
  { name: "Machamp", set: "Base Set", type: "Fighting", rarity: "Rare Holo", hp: 100 },
  { name: "Snorlax", set: "Jungle", type: "Colorless", rarity: "Rare Holo", hp: 90 },
  { name: "Eevee", set: "Jungle", type: "Colorless", rarity: "Common", hp: 50 },
  { name: "Rayquaza", set: "EX Deoxys", type: "Dragon", rarity: "Ultra Rare", hp: 110 },
  { name: "Lucario", set: "Diamond & Pearl", type: "Fighting", rarity: "Rare", hp: 90 },
];

export function seedIfEmpty(db: Database): void {
  const row = db.prepare("SELECT COUNT(*) AS n FROM cards").get() as { n: number };
  if (row.n > 0) return;
  const insert = db.transaction((cards: NewCard[]) => {
    for (const c of cards) createCard(db, c);
  });
  insert(SEED_CARDS);
}
