import { normalizeName, normalizeNumber } from "./normalize";

/**
 * A grader's free-text input, broken into the parts that can be read without
 * consulting the catalog.
 *
 * Graders type whatever is printed on the card, in no fixed order: "4/102",
 * "BS 4", "base1-4", "Charizard 4/102", "SV1a 001", "リザードン". Only two
 * shapes are unambiguous on their own — a number over a printed total, and a
 * source card ID — so those are extracted here. Everything else stays a token,
 * because telling a set code from a collector number ("SV1a" versus "TG01")
 * requires knowing which sets exist. The matcher settles that against the
 * catalog.
 */
export interface ParsedQuery {
  raw: string;
  /** A source card ID such as "base1-4", when the input clearly is one. */
  cardId?: string;
  /** Collector number from a "4/102" style token, normalized. */
  number?: string;
  /** The denominator printed on the card: the 102 in "4/102". */
  printedTotal?: number;
  /** Tokens not consumed above, in input order. */
  tokens: string[];
}

/** "4/102" or "SV001/198" — a collector number over the set's printed total. */
const NUMBER_OVER_TOTAL = /^([\p{L}\p{N}]+)\/(\d+)$/u;

/**
 * A source card ID: a set ID containing a digit, a hyphen, then a number.
 * The digit requirement keeps hyphenated Pokémon names ("Ho-Oh", "Porygon-Z")
 * out of this branch.
 */
const CARD_ID = /^([\p{L}\p{N}.]*\d[\p{L}\p{N}.]*)-(\d+[a-z]?)$/iu;

/**
 * A canonical card UID. New form: '<game>:<language>:<set>#<number>[#parallel]'
 * e.g. "pokemon:en:bs#4", "mtg:zhs:lea#1", "sports:en:set#38#haloref".
 * Language is 2–3 letters, optionally hyphenated (`zh-cn`, `pt-br`).
 * Legacy form without game ("en:bs#4") is still accepted so older grading
 * records keep working during migration.
 */
const CANONICAL_UID =
  /^(?:[a-z][a-z0-9]*:)?[a-z]{2,3}(?:-[a-z]{2,4})?:[^\s#]+#\S+$/i;

/** Digits only, so unambiguously a collector number. */
const PURE_NUMBER = /^\d{1,5}$/;

/** Digits with a short letter prefix or suffix: "TG01", "H1", "SV001", "1a". */
const MIXED_NUMBER = /^[a-z]{0,4}\d{1,4}[a-z]{0,2}$/i;

export function parseCardQuery(raw: string): ParsedQuery {
  const trimmed = (raw ?? "").trim();
  const parsed: ParsedQuery = { raw: trimmed, tokens: [] };

  for (const token of trimmed.split(/\s+/).filter(Boolean)) {
    const overTotal = token.match(NUMBER_OVER_TOTAL);
    if (overTotal && !parsed.number) {
      parsed.number = normalizeNumber(overTotal[1]);
      parsed.printedTotal = Number(overTotal[2]);
      continue;
    }

    if (!parsed.cardId && (CANONICAL_UID.test(token) || CARD_ID.test(token))) {
      parsed.cardId = token.toLowerCase();
      continue;
    }

    parsed.tokens.push(token);
  }

  return parsed;
}

/**
 * Picks the token most likely to be a collector number, from the tokens left
 * after set names have been claimed.
 *
 * Digits alone are always a number. A token mixing letters and digits is only
 * read as a number when something else in the input can identify the card,
 * otherwise a lone set code like "SV1a" would be mistaken for one.
 */
export function pickNumberToken(tokens: string[]): string | undefined {
  const pure = tokens.find((t) => PURE_NUMBER.test(t));
  if (pure) return pure;
  if (tokens.length > 1) return tokens.find((t) => MIXED_NUMBER.test(t));
  return undefined;
}

/**
 * Every contiguous run of tokens, longest first, so multi-word set names
 * ("Team Rocket") are tried before their individual words.
 */
export function contiguousPhrases(tokens: string[]): string[] {
  const phrases: string[] = [];
  for (let length = tokens.length; length >= 1; length--) {
    for (let start = 0; start + length <= tokens.length; start++) {
      phrases.push(tokens.slice(start, start + length).join(" "));
    }
  }
  return phrases;
}

/**
 * True when the input is long enough for the trigram index to match on.
 * FTS5's trigram tokenizer indexes three-character sequences, so shorter
 * fragments need a LIKE scan instead.
 */
export function isTrigramSearchable(text: string): boolean {
  return normalizeName(text).length >= 3;
}
