/**
 * Sports-card grading helpers.
 *
 * Operators grade sports cards as three fields:
 *   set name  — "2025-26 TOPPS MANCHESTER UNITED TEAM SET"
 *   card line — "SIR DAVID BECKHAM - HALO REF." or
 *               "SHAWN MICHAELS – AUTO - RUBY REF. – 09/15"
 *   number    — "38" or "SSL-SM"
 *
 * The card line must NOT treat "09/15" as a Pokémon-style printed total; it is
 * a serial / print-run of that parallel.
 */

export interface SportsCardLine {
  raw: string;
  subjectName: string;
  parallel?: string;
  notations: string[];
  /** Serial number of this copy, e.g. "09". */
  serialNumber?: string;
  /** Print run size, e.g. 15 from "09/15". */
  printRun?: number;
  /** Reconstructed display label. */
  displayName: string;
}

export interface SportsSetHints {
  raw: string;
  productYear?: string;
  manufacturer?: string;
}

const DASH = /\s*[-–—]\s*/;
const SERIAL = /^(\d{1,4})\s*\/\s*(\d{1,4})$/;
const NOTATION_TOKENS = new Set([
  "auto",
  "autograph",
  "au",
  "rc",
  "rookie",
  "sp",
  "ssp",
  "relic",
  "patch",
  "jersey",
  "memorabilia",
]);

const MANUFACTURERS = [
  "TOPPS",
  "PANINI",
  "UPPER DECK",
  "SKYBOX",
  "BOWMAN",
  "DONRUSS",
  "FLEER",
];

/**
 * Split a graded card-name line into subject, notations, parallel and serial.
 */
export function parseSportsCardLine(raw: string): SportsCardLine {
  const trimmed = (raw ?? "").trim();
  const parts = trimmed
    .split(DASH)
    .map((part) => part.trim())
    .filter(Boolean);

  let subjectName = parts[0] ?? trimmed;
  const notations: string[] = [];
  let parallel: string | undefined;
  let serialNumber: string | undefined;
  let printRun: number | undefined;

  for (let i = 1; i < parts.length; i++) {
    const part = parts[i];
    const serial = part.match(SERIAL);
    if (serial) {
      serialNumber = serial[1];
      printRun = Number(serial[2]);
      continue;
    }
    const folded = part.replace(/\./g, "").trim().toLowerCase();
    if (NOTATION_TOKENS.has(folded)) {
      notations.push(part.replace(/\./g, "").trim().toUpperCase());
      continue;
    }
    // Anything else after the subject is treated as a parallel label.
    parallel = part.replace(/\.$/, "").trim();
  }

  if (!subjectName && trimmed) subjectName = trimmed;

  return {
    raw: trimmed,
    subjectName,
    parallel,
    notations,
    serialNumber,
    printRun,
    displayName: trimmed,
  };
}

/**
 * Pull season / year and manufacturer hints out of a sports set title.
 */
export function parseSportsSetName(raw: string): SportsSetHints {
  const trimmed = (raw ?? "").trim();
  const year =
    trimmed.match(/\b(\d{4}-\d{2})\b/)?.[1] ??
    trimmed.match(/\b((?:19|20)\d{2})\b/)?.[1];

  const upper = trimmed.toUpperCase();
  let manufacturer: string | undefined;
  for (const name of MANUFACTURERS) {
    if (upper.includes(name)) {
      manufacturer = name === "UPPER DECK" ? "Upper Deck" : titleCase(name);
      break;
    }
  }

  return { raw: trimmed, productYear: year, manufacturer };
}

function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
