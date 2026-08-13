import { describe, expect, it } from "vitest";
import { buildTestCatalog } from "./__fixtures__/catalog";
import { searchCards } from "./catalog";
import { normalizeSportsNumber } from "./normalize";
import { parseSportsCardLine, parseSportsSetName } from "./sports";

describe("parseSportsCardLine", () => {
  it("splits subject and parallel for Beckham halo ref", () => {
    const line = parseSportsCardLine("SIR DAVID BECKHAM - HALO REF.");
    expect(line.subjectName).toBe("SIR DAVID BECKHAM");
    expect(line.parallel).toBe("HALO REF");
    expect(line.notations).toEqual([]);
    expect(line.printRun).toBeUndefined();
  });

  it("treats 09/15 as a print run, not a Pokémon printed total", () => {
    const line = parseSportsCardLine(
      "SHAWN MICHAELS – AUTO - RUBY REF. – 09/15"
    );
    expect(line.subjectName).toBe("SHAWN MICHAELS");
    expect(line.notations).toContain("AUTO");
    expect(line.parallel).toBe("RUBY REF");
    expect(line.serialNumber).toBe("09");
    expect(line.printRun).toBe(15);
  });

  it("handles en-dash and em-dash separators", () => {
    const line = parseSportsCardLine("PLAYER — PATCH – GOLD");
    expect(line.subjectName).toBe("PLAYER");
    expect(line.notations.map((n) => n.toUpperCase())).toContain("PATCH");
    expect(line.parallel).toBe("GOLD");
  });
});

describe("parseSportsSetName", () => {
  it("extracts season and manufacturer from Topps Man Utd", () => {
    const set = parseSportsSetName("2025-26 TOPPS MANCHESTER UNITED TEAM SET");
    expect(set.productYear).toBe("2025-26");
    expect(set.manufacturer).toBe("Topps");
  });

  it("extracts year and manufacturer from Panini Flawless WWE", () => {
    const set = parseSportsSetName("2024 PANINI FLAWLESS WWE");
    expect(set.productYear).toBe("2024");
    expect(set.manufacturer).toBe("Panini");
  });
});

describe("normalizeSportsNumber", () => {
  it("keeps hyphens that are part of the number", () => {
    expect(normalizeSportsNumber("SSL-SM")).toBe("ssl-sm");
    expect(normalizeSportsNumber("ssl-sm")).toBe("ssl-sm");
  });

  it("still collapses padded digit-only numbers", () => {
    expect(normalizeSportsNumber("038")).toBe("38");
  });
});

describe("sports fixture rows", () => {
  it("includes base and Halo Ref Beckham #38 as distinct printings", () => {
    const db = buildTestCatalog();
    const { cards } = searchCards(db, {
      game: "sports",
      set: "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
      number: "38",
    });
    const uids = cards.map((c) => c.card_uid).sort();
    expect(uids).toEqual([
      "sports:en:202526toppsmanchesterunitedteamset#38",
      "sports:en:202526toppsmanchesterunitedteamset#38#haloref",
    ]);
  });

  it("includes Michaels SSL-SM ruby auto with serial 09/15", () => {
    const db = buildTestCatalog();
    const { cards } = searchCards(db, {
      game: "sports",
      set: "2024 PANINI FLAWLESS WWE",
      number: "SSL-SM",
    });
    const ruby = cards.find((c) => c.parallel === "RUBY REF");
    expect(ruby?.card_uid).toBe("sports:en:2024paniniflawlesswwe#SSL-SM#rubyref");
    expect(ruby?.serial_number).toBe("09");
    expect(ruby?.print_run).toBe(15);
    expect(ruby?.notations).toBe("AUTO");
  });
});
