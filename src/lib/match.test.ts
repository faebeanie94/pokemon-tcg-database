import type { Database } from "better-sqlite3";
import { beforeEach, describe, expect, it } from "vitest";
import { buildTestCatalog } from "./__fixtures__/catalog";
import { matchCards, resolveSetTokens } from "./match";

describe("matchCards", () => {
  let db: Database;

  beforeEach(() => {
    db = buildTestCatalog();
  });

  it("identifies a card from its name, number and printed total", () => {
    const result = matchCards(db, { query: "Charizard 4/102", language: "en" });

    expect(result.unambiguous).toBe(true);
    expect(result.candidates[0].card.card_uid).toBe("en:bs#4");
    expect(result.candidates[0].matchedOn).toContain("collector number");
    expect(result.candidates[0].matchedOn).toContain("printed total");
    expect(result.candidates[0].matchedOn).toContain("name");
  });

  it("reports the same printing in several languages as needing a decision", () => {
    const result = matchCards(db, { query: "Charizard 4/102" });

    // The English, French and German Base Set cards are all card 4 of 102;
    // only the language tells them apart, and none was given.
    expect(result.unambiguous).toBe(false);
    expect(
      result.candidates.slice(0, 3).map((c) => c.card.language).sort()
    ).toEqual(["de", "en", "fr"]);
  });

  it("resolves a set abbreviation plus a number", () => {
    const result = matchCards(db, { query: "BS 4", language: "en" });

    expect(result.unambiguous).toBe(true);
    expect(result.candidates[0].card.card_uid).toBe("en:bs#4");
    expect(result.interpretation.number).toBe("4");
    expect(result.interpretation.sets[0].token).toBe("BS");
  });

  it("tells a set code apart from a collector number", () => {
    // "SV1a" is a Japanese set and "001" the card in it. Reading them the
    // other way round finds nothing.
    const result = matchCards(db, { query: "SV1a 001" });

    expect(result.unambiguous).toBe(true);
    expect(result.candidates[0].card.name).toBe("トロピウス");
    expect(result.interpretation.number).toBe("1");
    expect(result.interpretation.sets[0].setUids).toEqual(["ja:sv1a"]);
  });

  it("claims a multi-word set name before its individual words", () => {
    const result = matchCards(db, { query: "Team Rocket 4", language: "en" });

    expect(result.interpretation.sets[0].token).toBe("Team Rocket");
    expect(result.candidates[0].card.card_uid).toBe("en:tr#4");
    expect(result.unambiguous).toBe(true);
  });

  it("finds a set by a curated alias the source does not carry", () => {
    // TCGdex publishes no abbreviation for Japanese sets; the alias comes
    // from the curated workbook.
    const result = matchCards(db, { query: "Triplet Beat 001" });

    expect(result.candidates[0].card.card_uid).toBe("ja:sv1a#001");
    expect(result.unambiguous).toBe(true);
  });

  it("finds a translated card by its English name", () => {
    const result = matchCards(db, { query: "Blastoise", language: "fr" });

    expect(result.candidates[0].card.name).toBe("Tortank");
    expect(result.candidates[0].matchedOn).toContain("name");
  });

  it("matches a Chinese card by its English name and the other way round", () => {
    const byEnglish = matchCards(db, { query: "Bulbasaur", language: "zh-cn" });
    expect(byEnglish.candidates[0].card.name).toBe("妙蛙种子");

    const byChinese = matchCards(db, { query: "妙蛙种子" });
    expect(byChinese.candidates[0].card.english_name).toBe("Bulbasaur");
  });

  it("matches part of a Japanese name", () => {
    const result = matchCards(db, { query: "リザードン", language: "ja" });

    expect(result.candidates[0].card.name).toBe("メガリザードンXex");
    expect(result.candidates[0].matchedOn).toContain("partial name");
  });

  it("treats a stated language as a filter, not a preference", () => {
    const result = matchCards(db, { query: "Charizard 4/102", language: "de" });

    expect(result.candidates.every((c) => c.card.language === "de")).toBe(true);
    expect(result.candidates[0].card.name).toBe("Glurak");
  });

  it("returns every language of a printing when given only a card ID", () => {
    const result = matchCards(db, { query: "base1-4" });

    expect(result.candidates).toHaveLength(3);
    expect(result.candidates.every((c) => c.matchedOn.includes("card ID"))).toBe(
      true
    );
    expect(result.unambiguous).toBe(false);
  });

  it("finds a card from its canonical UID", () => {
    const result = matchCards(db, { query: "en:bs#4" });

    expect(result.candidates[0].card.card_uid).toBe("en:bs#4");
    expect(result.candidates[0].matchedOn).toContain("card ID");
    expect(result.unambiguous).toBe(true);
  });

  it("does not guess when a bare number is all it has", () => {
    const result = matchCards(db, { query: "4" });

    expect(result.unambiguous).toBe(false);
    expect(result.candidates.length).toBeGreaterThan(1);
    expect(
      result.candidates.every((c) => c.matchedOn.includes("collector number"))
    ).toBe(true);
  });

  it("returns nothing for input that matches no card", () => {
    const result = matchCards(db, { query: "Snorlax" });

    expect(result.candidates).toEqual([]);
    expect(result.unambiguous).toBe(false);
  });

  it("accepts structured fields instead of free text", () => {
    const result = matchCards(db, {
      name: "Charizard",
      set: "base1",
      number: "004",
      language: "en",
    });

    expect(result.candidates[0].card.card_uid).toBe("en:bs#4");
    expect(result.unambiguous).toBe(true);
  });

  it("caps the number of candidates returned", () => {
    const result = matchCards(db, { query: "Charizard", limit: 2 });
    expect(result.candidates).toHaveLength(2);
  });
});

describe("resolveSetTokens", () => {
  it("resolves abbreviations, set IDs, set names and aliases", () => {
    const db = buildTestCatalog();

    expect(resolveSetTokens(db, ["BS"])[0].setUids.sort()).toEqual(["de:bs", "en:bs", "en:bs-1999", "fr:bs"]);
    expect(resolveSetTokens(db, ["base5"])[0].setUids).toEqual(["en:tr"]);
    expect(resolveSetTokens(db, ["team rocket"])[0].setUids).toEqual(["en:tr"]);
    expect(resolveSetTokens(db, ["Triplet Beat"])[0].setUids).toEqual(["ja:sv1a"]);
    expect(resolveSetTokens(db, ["Charizard"])).toEqual([]);
  });
});
