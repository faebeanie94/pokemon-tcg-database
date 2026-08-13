import { describe, expect, it } from "vitest";
import { normalizeName, normalizeNumber, normalizeSportsNumber } from "./normalize";

describe("normalizeName", () => {
  it("ignores case, accents and punctuation", () => {
    expect(normalizeName("Mr. Mime")).toBe("mrmime");
    expect(normalizeName("mr mime")).toBe("mrmime");
    expect(normalizeName("Farfetch'd")).toBe("farfetchd");
    expect(normalizeName("Pokémon")).toBe("pokemon");
    expect(normalizeName("Ho-Oh")).toBe("hooh");
  });

  it("treats accented and unaccented spellings as the same name", () => {
    expect(normalizeName("Dracaufeu")).toBe(normalizeName("DRACAUFEU"));
    expect(normalizeName("Flabébé")).toBe(normalizeName("Flabebe"));
  });

  it("keeps CJK names intact", () => {
    expect(normalizeName("リザードン")).toBe("リザードン");
    expect(normalizeName("妙蛙种子")).toBe("妙蛙种子");
  });

  it("keeps Japanese voiced sounds distinct", () => {
    expect(normalizeName("リザードン")).not.toBe(normalizeName("リサトン"));
    expect(normalizeName("バク")).not.toBe(normalizeName("ハク"));
  });

  it("folds full-width characters, which Japanese printings use", () => {
    expect(normalizeName("ＰＩＫＡＣＨＵ")).toBe("pikachu");
  });

  it("returns an empty string for missing input", () => {
    expect(normalizeName(undefined)).toBe("");
    expect(normalizeName(null)).toBe("");
    expect(normalizeName("   ")).toBe("");
  });
});

describe("normalizeNumber", () => {
  it("makes padded and unpadded numbers compare equal", () => {
    expect(normalizeNumber("001")).toBe("1");
    expect(normalizeNumber("1")).toBe("1");
    expect(normalizeNumber("010")).toBe("10");
  });

  it("keeps letter prefixes and suffixes, which distinguish real cards", () => {
    expect(normalizeNumber("TG01")).toBe("tg1");
    expect(normalizeNumber("H1")).toBe("h1");
    expect(normalizeNumber("1a")).toBe("1a");
    expect(normalizeNumber("SV001")).toBe("sv1");
  });

  it("does not conflate a plain number with a prefixed one", () => {
    expect(normalizeNumber("H1")).not.toBe(normalizeNumber("1"));
  });

  it("strips separators", () => {
    expect(normalizeNumber(" 004 ")).toBe("4");
    expect(normalizeNumber("SWSH-045")).toBe("swsh45");
  });
});

describe("normalizeSportsNumber", () => {
  it("keeps hyphens that are part of the number", () => {
    expect(normalizeSportsNumber("SSL-SM")).toBe("ssl-sm");
  });

  it("still collapses padded digit-only numbers", () => {
    expect(normalizeSportsNumber("038")).toBe("38");
  });
});
