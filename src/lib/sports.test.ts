import { describe, expect, it } from "vitest";
import type { Database } from "better-sqlite3";
import { beforeEach } from "vitest";
import { buildTestCatalog } from "./__fixtures__/catalog";
import { matchCards } from "./match";
import { normalizeSportsNumber } from "./normalize";
import { parseSportsCardLine, parseSportsSetName } from "./sports";

describe("parseSportsCardLine", () => {
  it("splits subject and parallel for Beckham halo ref", () => {
    const line = parseSportsCardLine("SIR DAVID BECKHAM - HALO REF.");
    expect(line.subject_name).toBe("SIR DAVID BECKHAM");
    expect(line.parallel).toBe("HALO REF");
    expect(line.notations).toEqual([]);
    expect(line.print_run).toBeUndefined();
  });

  it("parses Michaels auto ruby ref with serial as print run, not printed total", () => {
    const line = parseSportsCardLine(
      "SHAWN MICHAELS – AUTO - RUBY REF. – 09/15"
    );
    expect(line.subject_name).toBe("SHAWN MICHAELS");
    expect(line.notations).toContain("AUTO");
    expect(line.parallel).toBe("RUBY REF");
    expect(line.serial_number).toBe("09");
    expect(line.print_run).toBe(15);
  });

  it("handles en-dash and em-dash separators", () => {
    const line = parseSportsCardLine("PLAYER — PATCH – GOLD");
    expect(line.subject_name).toBe("PLAYER");
    expect(line.notations.map((n) => n.toUpperCase())).toContain("PATCH");
    expect(line.parallel).toBe("GOLD");
  });
});

describe("parseSportsSetName", () => {
  it("extracts season and manufacturer from Topps Man Utd", () => {
    const set = parseSportsSetName("2025-26 TOPPS MANCHESTER UNITED TEAM SET");
    expect(set.product_year).toBe("2025-26");
    expect(set.manufacturer).toBe("Topps");
  });

  it("extracts year and manufacturer from Panini Flawless WWE", () => {
    const set = parseSportsSetName("2024 PANINI FLAWLESS WWE");
    expect(set.product_year).toBe("2024");
    expect(set.manufacturer).toBe("Panini");
  });
});

describe("normalizeSportsNumber", () => {
  it("preserves hyphenated alphanumeric numbers", () => {
    expect(normalizeSportsNumber("SSL-SM")).toBe("ssl-sm");
    expect(normalizeSportsNumber("ssl-sm")).toBe("ssl-sm");
  });

  it("still collapses padded digit numbers", () => {
    expect(normalizeSportsNumber("038")).toBe("38");
  });
});

describe("sports matching", () => {
  let db: Database;

  beforeEach(() => {
    db = buildTestCatalog();
  });

  it("matches Beckham halo ref #38 unambiguously", () => {
    const result = matchCards(db, {
      game: "sports",
      set: "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
      name: "SIR DAVID BECKHAM - HALO REF.",
      number: "38",
    });

    expect(result.candidates[0]?.card.parallel).toBe("HALO REF");
    expect(result.candidates[0]?.card.card_number).toBe("38");
    expect(result.candidates[0]?.matchedOn).toEqual(
      expect.arrayContaining(["set", "collector number", "parallel"])
    );
    expect(result.unambiguous).toBe(true);
  });

  it("does not auto-accept a parallel when the input has no parallel", () => {
    const result = matchCards(db, {
      game: "sports",
      set: "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
      name: "SIR DAVID BECKHAM",
      number: "38",
    });

    const top = result.candidates[0];
    expect(top).toBeDefined();
    // Prefer the base printing when no parallel was given.
    expect(top!.card.parallel).toBeNull();
    expect(result.unambiguous).toBe(false);
  });

  it("matches Michaels SSL-SM ruby auto serial", () => {
    const result = matchCards(db, {
      game: "sports",
      set: "2024 PANINI FLAWLESS WWE",
      name: "SHAWN MICHAELS – AUTO - RUBY REF. – 09/15",
      number: "SSL-SM",
    });

    expect(result.candidates[0]?.card.card_number).toBe("SSL-SM");
    expect(result.candidates[0]?.card.parallel).toBe("RUBY REF");
    expect(result.candidates[0]?.card.serial_number).toBe("09");
    expect(result.candidates[0]?.card.print_run).toBe(15);
    expect(result.interpretation.print_run).toBe(15);
    expect(result.unambiguous).toBe(true);
  });
});
