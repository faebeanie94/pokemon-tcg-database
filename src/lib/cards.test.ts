import Database from "better-sqlite3";
import { beforeEach, describe, expect, it } from "vitest";
import {
  createCard,
  getCard,
  initSchema,
  listCards,
  seedIfEmpty,
  SEED_CARDS,
  ValidationError,
} from "./cards";

function freshDb() {
  const db = new Database(":memory:");
  initSchema(db);
  return db;
}

describe("cards data layer", () => {
  let db: Database.Database;

  beforeEach(() => {
    db = freshDb();
  });

  it("creates and reads a card back", () => {
    const created = createCard(db, {
      name: "Gengar",
      set: "Fossil",
      type: "Psychic",
      rarity: "Rare Holo",
      hp: 80,
    });
    expect(created.id).toBeGreaterThan(0);
    expect(created.name).toBe("Gengar");
    expect(created.hp).toBe(80);

    const fetched = getCard(db, created.id);
    expect(fetched?.name).toBe("Gengar");
  });

  it("rejects invalid type", () => {
    expect(() =>
      createCard(db, {
        name: "Bad",
        set: "X",
        type: "Nonsense",
        rarity: "Common",
      })
    ).toThrow(ValidationError);
  });

  it("rejects missing name", () => {
    expect(() =>
      createCard(db, { name: "  ", set: "X", type: "Fire", rarity: "Common" })
    ).toThrow(ValidationError);
  });

  it("filters by search term across name and set", () => {
    createCard(db, { name: "Pikachu", set: "Base Set", type: "Lightning", rarity: "Common" });
    createCard(db, { name: "Raichu", set: "Jungle", type: "Lightning", rarity: "Rare" });

    expect(listCards(db, { search: "pika" }).map((c) => c.name)).toEqual(["Pikachu"]);
    expect(listCards(db, { search: "jungle" }).map((c) => c.name)).toEqual(["Raichu"]);
  });

  it("filters by type", () => {
    createCard(db, { name: "Charizard", set: "Base Set", type: "Fire", rarity: "Rare Holo" });
    createCard(db, { name: "Squirtle", set: "Base Set", type: "Water", rarity: "Common" });

    const fireCards = listCards(db, { type: "Fire" });
    expect(fireCards).toHaveLength(1);
    expect(fireCards[0].name).toBe("Charizard");
  });

  it("seeds the database only when empty", () => {
    seedIfEmpty(db);
    expect(listCards(db)).toHaveLength(SEED_CARDS.length);
    // Running again must not duplicate.
    seedIfEmpty(db);
    expect(listCards(db)).toHaveLength(SEED_CARDS.length);
  });
});
