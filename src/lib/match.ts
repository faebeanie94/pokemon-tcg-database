import type { Database } from "better-sqlite3";
import { ftsQuery, requireCatalog, type CatalogCard } from "./catalog";
import { normalizeName, normalizeNumber, normalizeSetToken } from "./normalize";
import {
  contiguousPhrases,
  isTrigramSearchable,
  parseCardQuery,
  pickNumberToken,
  type ParsedQuery,
} from "./query";

/**
 * Card matching for the grading workflow: given whatever an operator can read
 * off a physical card, return the catalog rows it could be, best first.
 *
 * Rather than one clever query, this runs a handful of cheap targeted lookups
 * (by source ID, by number within a set, by number over printed total, by
 * name) and scores everything they turn up. Each candidate carries the reasons
 * it scored, so an operator can see *why* a row was suggested and the program
 * can decide whether the top hit is safe to accept automatically.
 */

export interface MatchRequest {
  /** Free-text input, e.g. "Charizard 4/102" or "リザードン". */
  query?: string;
  /** Structured fields, used directly when the caller already has them. */
  name?: string;
  language?: string;
  set?: string;
  number?: string;
  printedTotal?: number;
  cardId?: string;
  limit?: number;
}

export interface MatchCandidate {
  card: CatalogCard;
  score: number;
  /** Human-readable reasons the row scored, for operator review. */
  matchedOn: string[];
}

export interface MatchResponse {
  /** How the free text was read, so the caller can show it back. */
  interpretation: Interpretation;
  candidates: MatchCandidate[];
  /**
   * True when exactly one candidate is a decisive match: it clears the
   * confidence bar and is clearly ahead of the runner-up. A grading program
   * can accept these without a human deciding.
   */
  unambiguous: boolean;
}

export interface Interpretation {
  cardId?: string;
  name?: string;
  number?: string;
  printedTotal?: number;
  language?: string;
  /** Set tokens that were recognised against the catalog. */
  sets: { token: string; setUids: string[] }[];
}

const POINTS = {
  cardId: 60,
  number: 25,
  printedTotal: 15,
  set: 30,
  nameExact: 30,
  nameContains: 12,
} as const;

/**
 * A top candidate must reach this score and beat the runner-up by this gap.
 * The bar is set so that a known set plus a collector number clears it, since
 * together those identify a printing outright.
 */
const CONFIDENT_SCORE = POINTS.set + POINTS.number;
const CONFIDENT_GAP = 15;

const CANDIDATE_CAP = 400;

export function matchCards(db: Database, request: MatchRequest): MatchResponse {
  requireCatalog(db);
  const limit = Math.min(Math.max(request.limit ?? 10, 1), 100);
  const parsed = request.query ? parseCardQuery(request.query) : emptyParse();

  const cardId = request.cardId ?? parsed.cardId;
  const printedTotal = request.printedTotal ?? parsed.printedTotal;
  const language = request.language?.trim() || undefined;

  // Which tokens name a set is decided by the catalog, not by their shape, so
  // that happens before a collector number or card name is read out of what
  // remains. Otherwise the set code in "SV1a 001" looks exactly like a number.
  const { resolvedSets, remainingTokens } = request.set
    ? {
        resolvedSets: resolveSetTokens(db, [request.set]),
        remainingTokens: parsed.tokens,
      }
    : claimSetTokens(db, parsed.tokens);
  const setUids = [...new Set(resolvedSets.flatMap((s) => s.setUids))];

  const numberToken =
    request.number || parsed.number ? undefined : pickNumberToken(remainingTokens);
  const number = request.number
    ? normalizeNumber(request.number)
    : (parsed.number ?? (numberToken ? normalizeNumber(numberToken) : undefined));

  const nameText = (
    request.name ?? remainingTokens.filter((t) => t !== numberToken).join(" ")
  ).trim();
  const nameNorm = normalizeName(nameText);

  const interpretation: Interpretation = {
    cardId,
    name: nameText || undefined,
    number,
    printedTotal,
    language,
    sets: resolvedSets,
  };

  const signals: Signals = {
    cardId,
    number,
    printedTotal,
    setUids,
    nameNorm,
    nameText,
    language,
  };

  const candidates = new Map<string, MatchCandidate>();
  for (const card of gatherCandidates(db, signals)) {
    // A caller who states the language is holding the card, so treat it as a
    // filter rather than a preference.
    if (language && card.language !== language) continue;
    if (!candidates.has(card.card_uid)) {
      candidates.set(card.card_uid, { card, score: 0, matchedOn: [] });
    }
  }

  for (const candidate of candidates.values()) {
    scoreCandidate(candidate, signals);
  }

  const ranked = [...candidates.values()]
    .filter((c) => c.score > 0)
    .sort(
      (a, b) =>
        b.score - a.score ||
        a.card.language.localeCompare(b.card.language) ||
        a.card.set_uid.localeCompare(b.card.set_uid)
    );

  const top = ranked[0];
  const runnerUp = ranked[1];
  const unambiguous =
    !!top &&
    top.score >= CONFIDENT_SCORE &&
    (!runnerUp || top.score - runnerUp.score >= CONFIDENT_GAP);

  return { interpretation, candidates: ranked.slice(0, limit), unambiguous };
}

interface Signals {
  cardId?: string;
  number?: string;
  printedTotal?: number;
  setUids: string[];
  nameNorm: string;
  nameText: string;
  language?: string;
}

const SELECT_CARD = `
  SELECT c.card_uid, c.set_uid, c.language,
         s.name AS set_name, s.name_en AS set_name_en, s.abbreviation AS set_code,
         s.series_name, s.card_count_official AS printed_total,
         c.number AS card_number, c.name,
         COALESCE(c.name_en, CASE WHEN c.language = 'en' THEN c.name END) AS english_name,
         c.card_id, c.sources
    FROM cards c
    JOIN sets s ON s.set_uid = c.set_uid`;

/** Runs the targeted lookups and returns every row worth scoring. */
function gatherCandidates(db: Database, signals: Signals): CatalogCard[] {
  const { cardId, number, printedTotal, setUids, nameNorm, nameText } = signals;
  const found: CatalogCard[] = [];

  if (cardId) {
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD} WHERE lower(c.card_id) = ? OR lower(c.card_uid) = ? LIMIT ?`
        )
        .all(cardId.toLowerCase(), cardId.toLowerCase(), CANDIDATE_CAP) as CatalogCard[])
    );
  }

  if (number && setUids.length) {
    const placeholders = setUids.map(() => "?").join(", ");
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE mc.number_norm = ? AND c.set_uid IN (${placeholders}) LIMIT ?`
        )
        .all(number, ...setUids, CANDIDATE_CAP) as CatalogCard[])
    );
  }

  if (number && printedTotal) {
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE mc.number_norm = ? AND s.card_count_official = ? LIMIT ?`
        )
        .all(number, printedTotal, CANDIDATE_CAP) as CatalogCard[])
    );
  }

  if (nameNorm) {
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE mc.name_norm = ? OR mc.name_en_norm = ? LIMIT ?`
        )
        .all(nameNorm, nameNorm, CANDIDATE_CAP) as CatalogCard[])
    );

    if (isTrigramSearchable(nameText)) {
      found.push(
        ...(db
          .prepare(
            `${SELECT_CARD}
               JOIN cards_fts ON cards_fts.card_uid = c.card_uid
              WHERE cards_fts MATCH ? LIMIT ?`
          )
          .all(ftsQuery(nameText), CANDIDATE_CAP) as CatalogCard[])
      );
    }
  }

  // A bare number with nothing else to go on matches one card in almost every
  // set. Still worth answering, but every hit ties on score, so the result is
  // reported as ambiguous and the operator picks.
  if (!found.length && number) {
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE mc.number_norm = ? LIMIT ?`
        )
        .all(number, CANDIDATE_CAP) as CatalogCard[])
    );
  }

  return found;
}

function scoreCandidate(candidate: MatchCandidate, signals: Signals): void {
  const { card } = candidate;
  const { cardId, number, printedTotal, setUids, nameNorm } = signals;

  if (cardId) {
    const wanted = cardId.toLowerCase();
    if (
      card.card_id?.toLowerCase() === wanted ||
      card.card_uid.toLowerCase() === wanted
    ) {
      candidate.score += POINTS.cardId;
      candidate.matchedOn.push("card ID");
    }
  }

  if (number && normalizeNumber(card.card_number) === number) {
    candidate.score += POINTS.number;
    candidate.matchedOn.push("collector number");
  }

  if (printedTotal && card.printed_total === printedTotal) {
    candidate.score += POINTS.printedTotal;
    candidate.matchedOn.push("printed total");
  }

  if (setUids.length && setUids.includes(card.set_uid)) {
    candidate.score += POINTS.set;
    candidate.matchedOn.push("set");
  }

  if (nameNorm) {
    const cardNameNorm = normalizeName(card.name);
    const englishNorm = normalizeName(card.english_name);
    if (cardNameNorm === nameNorm || englishNorm === nameNorm) {
      candidate.score += POINTS.nameExact;
      candidate.matchedOn.push("name");
    } else if (
      nameNorm.length >= 3 &&
      (cardNameNorm.includes(nameNorm) || englishNorm.includes(nameNorm))
    ) {
      candidate.score += POINTS.nameContains;
      candidate.matchedOn.push("partial name");
    } else if (
      nameNorm.length >= 3 &&
      (normalizeName(card.set_name).includes(nameNorm) ||
        normalizeName(card.set_name_en).includes(nameNorm))
    ) {
      candidate.score += POINTS.nameContains;
      candidate.matchedOn.push("set name");
    }
  }
}

/**
 * Looks each token up as a set code, canonical UID, source identifier, or local
 * or English set name. A token like "BS" resolves to Base Set in every language
 * that uses that code.
 */
export function resolveSetTokens(
  db: Database,
  tokens: string[]
): { token: string; setUids: string[] }[] {
  const resolved: { token: string; setUids: string[] }[] = [];
  const stmt = db.prepare(
    "SELECT DISTINCT set_uid FROM match_sets WHERE token_norm = ? LIMIT 50"
  );

  for (const token of tokens) {
    const norm = normalizeSetToken(token);
    if (!norm) continue;
    const rows = stmt.all(norm) as { set_uid: string }[];
    if (rows.length) {
      resolved.push({ token, setUids: rows.map((r) => r.set_uid) });
    }
  }

  return resolved;
}

/**
 * Claims the longest runs of tokens that name a set, and returns the tokens
 * left over. Longest-first means "Team Rocket" is recognised as one set rather
 * than as the words "team" and "rocket".
 */
function claimSetTokens(
  db: Database,
  tokens: string[]
): {
  resolvedSets: { token: string; setUids: string[] }[];
  remainingTokens: string[];
} {
  const resolvedSets: { token: string; setUids: string[] }[] = [];
  const claimed = new Set<string>();

  for (const phrase of contiguousPhrases(tokens)) {
    const words = phrase.split(" ");
    if (words.some((w) => claimed.has(w))) continue;

    const [match] = resolveSetTokens(db, [phrase]);
    if (match) {
      resolvedSets.push(match);
      for (const word of words) claimed.add(word);
    }
  }

  return { resolvedSets, remainingTokens: tokens.filter((t) => !claimed.has(t)) };
}

function emptyParse(): ParsedQuery {
  return { raw: "", tokens: [] };
}
