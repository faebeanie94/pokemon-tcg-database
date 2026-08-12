import { describe, expect, it } from "vitest";
import {
  contiguousPhrases,
  isTrigramSearchable,
  parseCardQuery,
  pickNumberToken,
} from "./query";

describe("parseCardQuery", () => {
  it("reads a collector number over a printed total", () => {
    const parsed = parseCardQuery("4/102");
    expect(parsed.number).toBe("4");
    expect(parsed.printedTotal).toBe(102);
    expect(parsed.tokens).toEqual([]);
  });

  it("keeps the name alongside a number", () => {
    const parsed = parseCardQuery("Charizard 4/102");
    expect(parsed.number).toBe("4");
    expect(parsed.printedTotal).toBe(102);
    expect(parsed.tokens).toEqual(["Charizard"]);
  });

  it("recognises a source card ID", () => {
    expect(parseCardQuery("base1-4").cardId).toBe("base1-4");
    expect(parseCardQuery("SV1a-001").cardId).toBe("sv1a-001");
  });

  it("does not mistake a hyphenated name for a card ID", () => {
    const parsed = parseCardQuery("Ho-Oh");
    expect(parsed.cardId).toBeUndefined();
    expect(parsed.tokens).toEqual(["Ho-Oh"]);
  });

  it("leaves ambiguous tokens for the catalog to settle", () => {
    // "SV1a" is a set code and "001" a number, but that is only knowable
    // from the catalog, so both stay as tokens here.
    expect(parseCardQuery("SV1a 001").tokens).toEqual(["SV1a", "001"]);
  });

  it("handles empty input", () => {
    const parsed = parseCardQuery("   ");
    expect(parsed.tokens).toEqual([]);
    expect(parsed.number).toBeUndefined();
  });
});

describe("pickNumberToken", () => {
  it("prefers a token of digits only", () => {
    expect(pickNumberToken(["Charizard", "4"])).toBe("4");
    expect(pickNumberToken(["001"])).toBe("001");
  });

  it("accepts a mixed token when other tokens narrow the card down", () => {
    expect(pickNumberToken(["Umbreon", "TG01"])).toBe("TG01");
  });

  it("does not read a lone mixed token as a number", () => {
    // A single "SV1a" is far more likely to be a set code than a number.
    expect(pickNumberToken(["SV1a"])).toBeUndefined();
  });

  it("returns undefined when no token looks like a number", () => {
    expect(pickNumberToken(["Mr.", "Mime"])).toBeUndefined();
  });
});

describe("contiguousPhrases", () => {
  it("returns longer runs before shorter ones", () => {
    expect(contiguousPhrases(["Team", "Rocket", "4"])).toEqual([
      "Team Rocket 4",
      "Team Rocket",
      "Rocket 4",
      "Team",
      "Rocket",
      "4",
    ]);
  });

  it("handles a single token", () => {
    expect(contiguousPhrases(["Jungle"])).toEqual(["Jungle"]);
  });
});

describe("isTrigramSearchable", () => {
  it("requires three indexable characters", () => {
    expect(isTrigramSearchable("Pikachu")).toBe(true);
    expect(isTrigramSearchable("リザードン")).toBe(true);
    expect(isTrigramSearchable("ex")).toBe(false);
    expect(isTrigramSearchable("a-b")).toBe(false);
  });
});
