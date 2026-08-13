import type { Database } from "better-sqlite3";
import { beforeEach, describe, expect, it } from "vitest";
import { buildTestCatalog } from "./__fixtures__/catalog";
import {
  canonicalBuiltAt,
  countCards,
  getCard,
  isIndexStale,
  listGames,
  listLanguages,
  listSets,
  searchCards,
} from "./catalog";

describe("searchCards", () => {
  let db: Database;

  beforeEach(() => {
    db = buildTestCatalog();
  });

  it("finds cards by a fragment of the name", () => {
    const { cards } = searchCards(db, { q: "chariz", language: "en" });
    expect(cards.map((c) => c.set_uid).sort()).toEqual(["pokemon:en:b2", "pokemon:en:bs", "pokemon:en:tr"]);
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

  it("filters by set given a code, canonical UID or source ID", () => {
    expect(searchCards(db, { set: "pokemon:en:tr" }).total).toBe(1);
    expect(searchCards(db, { set: "B2" }).total).toBe(1);
    expect(searchCards(db, { set: "base5" }).total).toBe(1);
    expect(searchCards(db, { set: "team rocket" }).total).toBe(1);
  });

  it("scopes search to a game so shared set codes do not collide", () => {
    const pokemon = searchCards(db, { set: "BS", game: "pokemon", language: "en", number: "4" });
    const mtg = searchCards(db, { set: "BS", game: "mtg", language: "en", number: "4" });
    expect(pokemon.cards.map((c) => c.card_uid)).toEqual(["pokemon:en:bs#4"]);
    expect(mtg.cards.map((c) => c.card_uid)).toEqual(["mtg:en:bs#4"]);
  });

  it("filters by collector number regardless of padding", () => {
    const padded = searchCards(db, { number: "001", language: "ja" });
    const bare = searchCards(db, { number: "1", language: "ja" });
    expect(padded.total).toBe(bare.total);
    expect(padded.cards[0].name).toBe("トロピウス");
  });

  it("exposes the English name of an English card", () => {
    // English printings carry no separate English name in the build.
    const { cards } = searchCards(db, { set: "pokemon:en:bs", number: "4" });
    expect(cards[0].english_name).toBe("Charizard");
  });

  it("paginates and reports the full total", () => {
    const firstPage = searchCards(db, { q: "Charizard", limit: 2, offset: 0 });
    const secondPage = searchCards(db, { q: "Charizard", limit: 2, offset: 2 });

    expect(firstPage.total).toBeGreaterThan(2);
    expect(firstPage.total).toBe(secondPage.total);
    expect(firstPage.cards).toHaveLength(2);
    expect(firstPage.cards.map((c) => c.card_uid)).not.toEqual(
      secondPage.cards.map((c) => c.card_uid)
    );
  });

  it("caps an oversized limit", () => {
    expect(searchCards(db, { limit: 10_000 }).limit).toBe(200);
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
    expect(listSets(db, {}).length).toBe(11);
    expect(
      listSets(db, { language: "en" })
        .map((s) => s.set_uid)
        .sort()
    ).toEqual([
      "mtg:en:bs",
      "pokemon:en:b2",
      "pokemon:en:bs",
      "pokemon:en:bs-1999",
      "pokemon:en:tr",
      "sports:en:2024paniniflawlesswwe",
      "sports:en:202526toppsmanchesterunitedteamset",
    ]);
    expect(
      listSets(db, { game: "pokemon", language: "en" })
        .map((s) => s.set_uid)
        .sort()
    ).toEqual(["pokemon:en:b2", "pokemon:en:bs", "pokemon:en:bs-1999", "pokemon:en:tr"]);
    expect(listSets(db, { game: "mtg" }).map((s) => s.set_uid)).toEqual(["mtg:en:bs"]);
  });

  it("lists games with card counts", () => {
    const games = listGames(buildTestCatalog());
    expect(games.map((g) => g.game).sort()).toEqual(["mtg", "pokemon", "sports"]);
    expect(games.find((g) => g.game === "mtg")?.kind).toBe("tcg");
    expect(games.find((g) => g.game === "sports")?.kind).toBe("sports");
  });

  it("finds a set by code or name fragment", () => {
    const db = buildTestCatalog();
    expect(listSets(db, { q: "Rocket" }).map((s) => s.set_uid)).toEqual(["pokemon:en:tr"]);
    expect(listSets(db, { q: "B2" }).map((s) => s.set_uid)).toEqual(["pokemon:en:b2"]);
  });

  it("reads a single card by its canonical UID", () => {
    const db = buildTestCatalog();
    expect(getCard(db, "pokemon:en:tr#4")?.name).toBe("Dark Charizard");
    expect(getCard(db, "en:tr#999")).toBeUndefined();
  });
});

describe("match index freshness", () => {
  it("is fresh once built from the current card data", () => {
    const db = buildTestCatalog();
    expect(canonicalBuiltAt(db)).toBe("2026-01-01T00:00:00Z");
    expect(isIndexStale(db)).toBe(false);
  });

  it("goes stale when the card data is rebuilt underneath it", () => {
    const db = buildTestCatalog();
    // What the Python service does when it swaps in a fresh build.
    db.prepare("UPDATE build_info SET value = ? WHERE key = 'built_at'").run(
      "2026-06-01T00:00:00Z"
    );
    expect(isIndexStale(db)).toBe(true);
  });
});
