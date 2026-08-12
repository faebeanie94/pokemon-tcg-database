import type { Database } from "better-sqlite3";
import { beforeEach, describe, expect, it } from "vitest";
import { buildTestCatalog } from "./__fixtures__/catalog";
import { countCards, getCard, listLanguages, listSets, searchCards } from "./catalog";

describe("searchCards", () => {
  let db: Database;

  beforeEach(() => {
    db = buildTestCatalog();
  });

  it("finds cards by a fragment of the name", () => {
    const { cards } = searchCards(db, { q: "chariz", language: "en" });
    expect(cards.map((c) => c.set_id).sort()).toEqual(["base1", "base4", "base5"]);
  });

  it("finds CJK names by substring", () => {
    const { cards } = searchCards(db, { q: "リザードン" });
    expect(cards).toHaveLength(1);
    expect(cards[0].name).toBe("メガリザードンXex");
  });

  it("falls back to a scan for fragments too short to be indexed", () => {
    // The trigram index cannot serve a two-character fragment.
    const { cards } = searchCards(db, { q: "ex", language: "ja" });
    expect(cards.map((c) => c.name)).toEqual(["メガリザードンXex"]);
  });

  it("searches the set name as well as the card name", () => {
    const { cards } = searchCards(db, { q: "Team Rocket" });
    expect(cards).toHaveLength(1);
    expect(cards[0].name).toBe("Dark Charizard");
  });

  it("filters by set given an ID, abbreviation or name", () => {
    expect(searchCards(db, { set: "base5" }).total).toBe(1);
    expect(searchCards(db, { set: "B2" }).total).toBe(1);
    expect(searchCards(db, { set: "team rocket" }).total).toBe(1);
  });

  it("filters by collector number regardless of padding", () => {
    const padded = searchCards(db, { number: "001", language: "ja" });
    const bare = searchCards(db, { number: "1", language: "ja" });
    expect(padded.total).toBe(bare.total);
    expect(padded.cards[0].name).toBe("トロピウス");
  });

  it("paginates and reports the full total", () => {
    const firstPage = searchCards(db, { q: "Charizard", limit: 2, offset: 0 });
    const secondPage = searchCards(db, { q: "Charizard", limit: 2, offset: 2 });

    expect(firstPage.total).toBeGreaterThan(2);
    expect(firstPage.total).toBe(secondPage.total);
    expect(firstPage.cards).toHaveLength(2);
    expect(firstPage.cards.map((c) => c.id)).not.toEqual(
      secondPage.cards.map((c) => c.id)
    );
  });

  it("caps an oversized limit", () => {
    const { limit } = searchCards(db, { limit: 10_000 });
    expect(limit).toBe(200);
  });

  it("returns everything when given no filters", () => {
    expect(searchCards(db, {}).total).toBe(countCards(db));
  });
});

describe("catalog metadata", () => {
  it("counts cards per language, busiest first", () => {
    const languages = listLanguages(buildTestCatalog());
    expect(languages[0].language).toBe("en");
    expect(languages.map((l) => l.language).sort()).toEqual([
      "de",
      "en",
      "fr",
      "ja",
      "zh-cn",
    ]);
  });

  it("lists sets and filters them by language", () => {
    const db = buildTestCatalog();
    expect(listSets(db, {}).length).toBe(7);
    expect(listSets(db, { language: "en" }).map((s) => s.set_id).sort()).toEqual([
      "base1",
      "base4",
      "base5",
    ]);
  });

  it("finds a set by abbreviation or name fragment", () => {
    const db = buildTestCatalog();
    expect(listSets(db, { q: "rocket" }).map((s) => s.set_id)).toEqual(["base5"]);
    expect(listSets(db, { q: "B2" }).map((s) => s.set_id)).toEqual(["base4"]);
  });

  it("reads a single card by its catalog ID", () => {
    const db = buildTestCatalog();
    const { cards } = searchCards(db, { set: "base5" });
    expect(getCard(db, cards[0].id)?.name).toBe("Dark Charizard");
    expect(getCard(db, 999_999)).toBeUndefined();
  });
});
