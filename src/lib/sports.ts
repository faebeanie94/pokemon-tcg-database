import { normalizeName } from "./normalize";

/**
 * Sports / entertainment cards are graded from three structured fields:
 * set title, card name line (subject + parallel + notations + serial), and
 * number. This module splits the name line and set title into those parts.
 */

const DASH_SPLIT = /\s*[-–—]\s*/;

/** Known insert / designation tokens that are not parallels. */
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

/** Serial like 09/15 or 9/99 — a print run, not a Pokémon printed total. */
const SERIAL_RE = /^(\d+)\s*\/\s*(\d+)$/;

const MANUFACTURERS = [
  "TOPPS",
  "PANINI",
  "UPPER DECK",
  "SKYBOX",
  "BOWMAN",
  "DONRUSS",
  "FLEER",
  "LEAF",
] as const;

export interface SportsCardLine {
  raw: string;
  subject_name: string;
  parallel?: string;
  notations: string[];
  serial_number?: string;
  print_run?: number;
  /** Rebuilt display line for matching against catalog display_name. */
  display_name: string;
}

export interface SportsSetName {
  raw: string;
  product_year?: string;
  manufacturer?: string;
  /** Remainder after year + manufacturer, useful as a title hint. */
  title_rest: string;
  norm: string;
}

/**
 * Split a graded sports card name line into subject, notations, parallel and
 * optional serial. Dashes (hyphen / en / em) are treated as segment separators.
 *
 * Examples:
 *   "SIR DAVID BECKHAM - HALO REF." -> subject + parallel HALO REF
 *   "SHAWN MICHAELS – AUTO - RUBY REF. – 09/15" -> subject, AUTO, RUBY REF, 09/15
 */
export function parseSportsCardLine(raw: string): SportsCardLine {
  const trimmed = (raw ?? "").trim();
  const segments = trimmed
    .split(DASH_SPLIT)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => s.replace(/\.$/, "").trim())
    .filter(Boolean);

  if (!segments.length) {
    return { raw: trimmed, subject_name: "", notations: [], display_name: "" };
  }

  const subject_name = segments[0];
  const notations: string[] = [];
  let parallel: string | undefined;
  let serial_number: string | undefined;
  let print_run: number | undefined;

  for (const segment of segments.slice(1)) {
    const serial = segment.match(SERIAL_RE);
    if (serial) {
      serial_number = serial[1].replace(/^0+(?=\d)/, "") === "" ? serial[1] : serial[1];
      // Keep zero-padded form as printed when short; store as given digits.
      serial_number = serial[1];
      print_run = Number(serial[2]);
      continue;
    }
    const key = normalizeName(segment);
    if (NOTATION_TOKENS.has(key)) {
      notations.push(segment.toUpperCase().replace(/\.$/, ""));
      continue;
    }
    // Last non-notation, non-serial segment wins as the parallel label.
    parallel = segment.toUpperCase().replace(/\.$/, "");
  }

  const displayParts = [subject_name, ...notations];
  if (parallel) displayParts.push(parallel);
  if (serial_number && print_run) displayParts.push(`${serial_number}/${print_run}`);

  return {
    raw: trimmed,
    subject_name,
    parallel,
    notations,
    serial_number,
    print_run,
    display_name: displayParts.join(" - "),
  };
}

/**
 * Pull season/year and manufacturer hints out of a full set title.
 *
 * "2025-26 TOPPS MANCHESTER UNITED TEAM SET" -> year 2025-26, manufacturer Topps
 * "2024 PANINI FLAWLESS WWE" -> year 2024, manufacturer Panini
 */
export function parseSportsSetName(raw: string): SportsSetName {
  const trimmed = (raw ?? "").trim();
  const upper = trimmed.toUpperCase();
  let rest = upper;
  let product_year: string | undefined;
  let manufacturer: string | undefined;

  const yearMatch = rest.match(/^(\d{4}(?:-\d{2})?)\b/);
  if (yearMatch) {
    product_year = yearMatch[1];
    rest = rest.slice(yearMatch[0].length).trim();
  }

  for (const maker of MANUFACTURERS) {
    if (rest.startsWith(maker + " ") || rest === maker) {
      manufacturer = maker
        .split(" ")
        .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
        .join(" ");
      rest = rest.slice(maker.length).trim();
      break;
    }
  }

  return {
    raw: trimmed,
    product_year,
    manufacturer,
    title_rest: rest,
    norm: normalizeName(trimmed),
  };
}
