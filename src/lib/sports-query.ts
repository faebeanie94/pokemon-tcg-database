/**
 * Sports grading query parser.
 *
 * Operators send three fields:
 *   set name  — "2025-26 TOPPS MANCHESTER UNITED TEAM SET"
 *   card line — "SIR DAVID BECKHAM - HALO REF." or
 *               "SHAWN MICHAELS – AUTO - RUBY REF. – 09/15"
 *   number    — "38" or "SSL-SM"
 *
 * "09/15" in the card line is a serial / print-run of that parallel, not a
 * Pokémon-style printed total.
 */

import { normalizeSportsNumber } from "./normalize";

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
  /** Season / year extracted from the set title, e.g. "2025-26" or "2024". */
  productYear?: string;
  manufacturer?: string;
  /** Set title with season and manufacturer tokens removed. */
  productName?: string;
}

export interface SportsNumberParse {
  raw: string;
  /** Normalized comparison key (hyphens kept for SSL-SM). */
  normalized: string;
  /** True when the number mixes letters and digits / hyphens. */
  alphanumeric: boolean;
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
  "UPPER DECK",
  "TOPPS",
  "PANINI",
  "SKYBOX",
  "BOWMAN",
  "DONRUSS",
  "FLEER",
  "LEAF",
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
      notations.push(normalizeNotation(part));
      continue;
    }
    // Anything else after the subject is treated as a parallel label.
    // Later parallels win when multiple appear (rare in real labels).
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
 * Pull season / year, manufacturer, and product-name remainder from a set title.
 */
export function parseSportsSetName(raw: string): SportsSetHints {
  const trimmed = (raw ?? "").trim();
  const year =
    trimmed.match(/\b(\d{4}-\d{2})\b/)?.[1] ??
    trimmed.match(/\b((?:19|20)\d{2})\b/)?.[1];

  const upper = trimmed.toUpperCase();
  let manufacturer: string | undefined;
  let manufacturerMatch: string | undefined;
  for (const name of MANUFACTURERS) {
    if (upper.includes(name)) {
      manufacturerMatch = name;
      manufacturer = name === "UPPER DECK" ? "Upper Deck" : titleCase(name);
      break;
    }
  }

  let productName: string | undefined = trimmed;
  if (year) {
    productName = productName.replace(new RegExp(`\\b${escapeRegExp(year)}\\b`, "i"), " ");
  }
  if (manufacturerMatch) {
    productName = productName.replace(
      new RegExp(escapeRegExp(manufacturerMatch), "i"),
      " "
    );
  }
  productName = productName.replace(/\s+/g, " ").trim() || undefined;

  return { raw: trimmed, productYear: year, manufacturer, productName };
}

/**
 * Accept pure digits and alphanumeric sports numbers (SSL-SM). Preserves the
 * hyphenated form for matching via normalizeSportsNumber.
 */
export function parseSportsNumber(raw: string): SportsNumberParse | undefined {
  const trimmed = (raw ?? "").trim();
  if (!trimmed) return undefined;
  const normalized = normalizeSportsNumber(trimmed);
  if (!normalized) return undefined;
  return {
    raw: trimmed,
    normalized,
    alphanumeric: /[a-z]/i.test(normalized) || normalized.includes("-"),
  };
}

function normalizeNotation(part: string): string {
  const cleaned = part.replace(/\./g, "").trim().toUpperCase();
  if (cleaned === "AU" || cleaned === "AUTOGRAPH") return "AUTO";
  if (cleaned === "ROOKIE") return "RC";
  return cleaned;
}

function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
