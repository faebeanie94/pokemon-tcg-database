import type { Database } from "better-sqlite3";
import { ftsQuery, requireCatalog, type CatalogCard } from "./catalog";
import {
  normalizeName,
  normalizeNumber,
  normalizeSetToken,
  normalizeSportsNumber,
} from "./normalize";
import {
  contiguousPhrases,
  isTrigramSearchable,
  parseCardQuery,
  pickNumberToken,
  type ParsedQuery,
} from "./query";
import { parseSportsCardLine } from "./sports";

/**
 * Card matching for the grading workflow: given whatever an operator can read
 * off a physical card, return the catalog rows it could be, best first.
 */

export interface MatchRequest {
  query?: string;
  name?: string;
  language?: string;
  game?: string;
  set?: string;
  number?: string;
  printedTotal?: number;
  cardId?: string;
  parallel?: string;
  subject?: string;
  /** Prefer sports grading path when true or when game === 'sports'. */
  sports?: boolean;
  limit?: number;
}

export interface MatchCandidate {
  card: CatalogCard;
  score: number;
  matchedOn: string[];
}

export interface MatchResponse {
  interpretation: Interpretation;
  candidates: MatchCandidate[];
  unambiguous: boolean;
}

export interface Interpretation {
  cardId?: string;
  name?: string;
  number?: string;
  printedTotal?: number;
  language?: string;
  game?: string;
  parallel?: string;
  subject?: string;
  serial_number?: string;
  print_run?: number;
  sets: { token: string; setUids: string[] }[];
}

const POINTS = {
  cardId: 60,
  number: 25,
  printedTotal: 15,
  set: 30,
  nameExact: 30,
  nameContains: 12,
  subject: 20,
  parallel: 25,
  serial: 15,
  baseNoParallel: 8,
} as const;

const CONFIDENT_SCORE = POINTS.set + POINTS.number;
const SPORTS_CONFIDENT_SCORE = POINTS.set + POINTS.number + POINTS.parallel;
const CONFIDENT_GAP = 15;
const CANDIDATE_CAP = 400;

export function matchCards(db: Database, request: MatchRequest): MatchResponse {
  requireCatalog(db);
  const sportsMode =
    request.sports === true ||
    request.game === "sports" ||
    (!!request.set && !!request.name && !!request.number && request.game === "sports");

  if (sportsMode || (request.game === "sports" && (request.set || request.name))) {
    return matchSportsCards(db, request);
  }

  // Structured sports-shaped call without game=sports still uses sports path
  // when set+name+number are all provided and name looks like a sports line.
  if (request.set && request.name && request.number && !request.query) {
    const line = parseSportsCardLine(request.name);
    if (line.parallel || line.notations.length || line.printRun) {
      return matchSportsCards(db, { ...request, sports: true });
    }
  }

  return matchTcgCards(db, request);
}

function matchSportsCards(db: Database, request: MatchRequest): MatchResponse {
  const limit = Math.min(Math.max(request.limit ?? 10, 1), 100);
  const setRaw = (request.set ?? "").trim();
  const nameRaw = (request.name ?? request.query ?? "").trim();
  const numberRaw = (request.number ?? "").trim();
  const language = request.language?.trim() || undefined;
  const game = request.game?.trim() || "sports";

  const line = nameRaw
    ? parseSportsCardLine(nameRaw)
    : {
        raw: "",
        subjectName: request.subject ?? "",
        parallel: request.parallel,
        notations: [] as string[],
        displayName: request.name ?? "",
      };

  const parallel = request.parallel?.trim() || line.parallel;
  const subject = request.subject?.trim() || line.subjectName;
  const numberNorm = numberRaw ? normalizeSportsNumber(numberRaw) : undefined;

  const setUids = setRaw ? resolveSportsSets(db, setRaw, game) : [];

  const interpretation: Interpretation = {
    name: line.displayName || nameRaw || undefined,
    number: numberNorm,
    language,
    game,
    parallel,
    subject: subject || undefined,
    serial_number: line.serialNumber,
    print_run: line.printRun,
    sets: setUids.length ? [{ token: setRaw, setUids }] : [],
  };

  const candidates = new Map<string, MatchCandidate>();
  for (const card of gatherSportsCandidates(db, {
    setUids,
    numberNorm,
    subjectNorm: normalizeName(subject),
    parallelNorm: normalizeName(parallel),
    displayNorm: normalizeName(line.displayName || nameRaw),
    game,
    language,
  })) {
    if (!candidates.has(card.card_uid)) {
      candidates.set(card.card_uid, { card, score: 0, matchedOn: [] });
    }
  }

  for (const candidate of candidates.values()) {
    scoreSportsCandidate(candidate, {
      setUids,
      numberNorm,
      subjectNorm: normalizeName(subject),
      parallelNorm: normalizeName(parallel),
      displayNorm: normalizeName(line.displayName || nameRaw),
      serial_number: line.serialNumber,
      print_run: line.printRun,
      inputHasParallel: !!parallel,
    });
  }

  const ranked = [...candidates.values()]
    .filter((c) => c.score > 0)
    .sort(
      (a, b) =>
        b.score - a.score ||
        a.card.card_uid.localeCompare(b.card.card_uid)
    );

  const top = ranked[0];
  const runnerUp = ranked[1];

  // Set + number alone is not enough when parallels exist for that number.
  let unambiguous =
    !!top &&
    top.score >= SPORTS_CONFIDENT_SCORE &&
    (!runnerUp || top.score - runnerUp.score >= CONFIDENT_GAP);

  if (unambiguous && top && !parallel && top.card.parallel) {
    unambiguous = false;
  }
  // Even if the base printing ranks first, do not auto-accept when the input
  // omitted a parallel and sibling parallels exist for the same number.
  if (unambiguous && top && !parallel && numberNorm) {
    const hasSiblingParallel = ranked.some(
      (c) =>
        c.card.set_uid === top.card.set_uid &&
        normalizeSportsNumber(c.card.card_number) === numberNorm &&
        !!c.card.parallel
    );
    if (hasSiblingParallel) unambiguous = false;
  }
  if (
    unambiguous &&
    top &&
    parallel &&
    !top.card.parallel &&
    runnerUp?.card.parallel &&
    normalizeName(runnerUp.card.parallel) === normalizeName(parallel)
  ) {
    unambiguous = false;
  }

  return { interpretation, candidates: ranked.slice(0, limit), unambiguous };
}

function resolveSportsSets(db: Database, setRaw: string, game: string): string[] {
  const norm = normalizeSetToken(setRaw);
  const exact = db
    .prepare(
      `SELECT DISTINCT set_uid FROM match_sets
        WHERE token_norm = ? AND (? = '' OR game = ?)
        LIMIT 50`
    )
    .all(norm, game, game) as { set_uid: string }[];
  if (exact.length) return exact.map((r) => r.set_uid);

  const like = db
    .prepare(
      `SELECT set_uid FROM sets
        WHERE game = ?
          AND (norm_name(name) = ? OR lower(name) = lower(?) OR name LIKE ?)
        LIMIT 50`
    )
    .all(game, norm, setRaw, `%${setRaw}%`) as { set_uid: string }[];
  return like.map((r) => r.set_uid);
}

interface SportsSignals {
  setUids: string[];
  numberNorm?: string;
  subjectNorm: string;
  parallelNorm: string;
  displayNorm: string;
  game: string;
  language?: string;
}

function gatherSportsCandidates(db: Database, signals: SportsSignals): CatalogCard[] {
  const found: CatalogCard[] = [];
  const { setUids, numberNorm, subjectNorm, parallelNorm, displayNorm, game, language } =
    signals;

  const langClause = language ? " AND c.language = ?" : "";
  const langParams = language ? [language] : [];

  if (numberNorm && setUids.length) {
    const placeholders = setUids.map(() => "?").join(", ");
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE mc.sports_number_norm = ? AND c.set_uid IN (${placeholders})
              AND c.game = ?${langClause}
            LIMIT ?`
        )
        .all(numberNorm, ...setUids, game, ...langParams, CANDIDATE_CAP) as CatalogCard[])
    );
  }

  if (!found.length && numberNorm) {
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE mc.sports_number_norm = ? AND c.game = ?${langClause}
            LIMIT ?`
        )
        .all(numberNorm, game, ...langParams, CANDIDATE_CAP) as CatalogCard[])
    );
  }

  if (displayNorm || subjectNorm) {
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE c.game = ?${langClause}
              AND (mc.display_norm = ? OR mc.subject_norm = ? OR mc.name_norm = ?)
            LIMIT ?`
        )
        .all(
          game,
          ...langParams,
          displayNorm || subjectNorm,
          subjectNorm,
          displayNorm || subjectNorm,
          CANDIDATE_CAP
        ) as CatalogCard[])
    );
  }

  if (parallelNorm && setUids.length && numberNorm) {
    const placeholders = setUids.map(() => "?").join(", ");
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE mc.parallel_norm = ? AND mc.sports_number_norm = ?
              AND c.set_uid IN (${placeholders}) AND c.game = ?${langClause}
            LIMIT ?`
        )
        .all(
          parallelNorm,
          numberNorm,
          ...setUids,
          game,
          ...langParams,
          CANDIDATE_CAP
        ) as CatalogCard[])
    );
  }

  return found;
}

function scoreSportsCandidate(
  candidate: MatchCandidate,
  signals: {
    setUids: string[];
    numberNorm?: string;
    subjectNorm: string;
    parallelNorm: string;
    displayNorm: string;
    serial_number?: string;
    print_run?: number;
    inputHasParallel: boolean;
  }
): void {
  const { card } = candidate;

  if (signals.numberNorm) {
    if (normalizeSportsNumber(card.card_number) === signals.numberNorm) {
      candidate.score += POINTS.number;
      candidate.matchedOn.push("collector number");
    }
  }

  if (signals.setUids.length && signals.setUids.includes(card.set_uid)) {
    candidate.score += POINTS.set;
    candidate.matchedOn.push("set");
  }

  if (signals.subjectNorm) {
    const subject = normalizeName(card.subject_name);
    if (subject === signals.subjectNorm || normalizeName(card.name).includes(signals.subjectNorm)) {
      candidate.score += POINTS.subject;
      candidate.matchedOn.push("subject");
    }
  }

  if (signals.displayNorm) {
    const display = normalizeName(card.display_name || card.name);
    if (display === signals.displayNorm) {
      candidate.score += POINTS.nameExact;
      candidate.matchedOn.push("display name");
    } else if (display.includes(signals.displayNorm) || signals.displayNorm.includes(display)) {
      candidate.score += POINTS.nameContains;
      candidate.matchedOn.push("partial display name");
    }
  }

  if (signals.parallelNorm) {
    if (normalizeName(card.parallel) === signals.parallelNorm) {
      candidate.score += POINTS.parallel;
      candidate.matchedOn.push("parallel");
    }
  } else if (!card.parallel) {
    // Prefer base cards when the input has no parallel.
    candidate.score += POINTS.baseNoParallel;
    candidate.matchedOn.push("base (no parallel)");
  } else if (!signals.inputHasParallel) {
    // Penalize parallel rows when the operator did not ask for one.
    candidate.score -= 10;
  }

  if (
    signals.serial_number &&
    signals.print_run &&
    card.serial_number === signals.serial_number &&
    card.print_run === signals.print_run
  ) {
    candidate.score += POINTS.serial;
    candidate.matchedOn.push("serial");
  }
}

function matchTcgCards(db: Database, request: MatchRequest): MatchResponse {
  const limit = Math.min(Math.max(request.limit ?? 10, 1), 100);
  const parsed = request.query ? parseCardQuery(request.query) : emptyParse();

  const cardId = request.cardId ?? parsed.cardId;
  const printedTotal = request.printedTotal ?? parsed.printedTotal;
  const language = request.language?.trim() || undefined;
  const game = request.game?.trim() || undefined;

  const { resolvedSets, remainingTokens } = request.set
    ? {
        resolvedSets: resolveSetTokens(db, [request.set], game),
        remainingTokens: parsed.tokens,
      }
    : claimSetTokens(db, parsed.tokens, game);
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
    game,
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
    game,
  };

  const candidates = new Map<string, MatchCandidate>();
  for (const card of gatherCandidates(db, signals)) {
    if (language && card.language !== language) continue;
    if (game && card.game !== game) continue;
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
  game?: string;
}

const SELECT_CARD = `
  SELECT c.card_uid, c.set_uid, c.game, c.language,
         s.name AS set_name, s.name_en AS set_name_en, s.abbreviation AS set_code,
         s.series_name, s.manufacturer, s.sport, s.product_year,
         s.card_count_official AS printed_total,
         c.number AS card_number, c.name,
         COALESCE(c.name_en, CASE WHEN c.language = 'en' THEN c.name END) AS english_name,
         c.subject_name, c.parallel, c.notations, c.serial_number, c.print_run,
         c.display_name, c.card_id, c.sources
    FROM cards c
    JOIN sets s ON s.set_uid = c.set_uid`;

function gatherCandidates(db: Database, signals: Signals): CatalogCard[] {
  const { cardId, number, printedTotal, setUids, nameNorm, nameText, game } = signals;
  const found: CatalogCard[] = [];
  const gameClause = game ? " AND c.game = ?" : "";
  const gameParam = game ? [game] : [];

  if (cardId) {
    const wanted = cardId.toLowerCase();
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
            WHERE (
              lower(c.card_id) = ?
              OR lower(c.card_uid) = ?
              OR lower(c.card_uid) LIKE '%:' || ?
            )${gameClause}
            LIMIT ?`
        )
        .all(wanted, wanted, wanted, ...gameParam, CANDIDATE_CAP) as CatalogCard[])
    );
  }

  if (number && setUids.length) {
    const placeholders = setUids.map(() => "?").join(", ");
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE mc.number_norm = ? AND c.set_uid IN (${placeholders})${gameClause} LIMIT ?`
        )
        .all(number, ...setUids, ...gameParam, CANDIDATE_CAP) as CatalogCard[])
    );
  }

  if (number && printedTotal) {
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE mc.number_norm = ? AND s.card_count_official = ?${gameClause} LIMIT ?`
        )
        .all(number, printedTotal, ...gameParam, CANDIDATE_CAP) as CatalogCard[])
    );
  }

  if (nameNorm) {
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE (mc.name_norm = ? OR mc.name_en_norm = ?)${gameClause} LIMIT ?`
        )
        .all(nameNorm, nameNorm, ...gameParam, CANDIDATE_CAP) as CatalogCard[])
    );

    if (isTrigramSearchable(nameText)) {
      found.push(
        ...(db
          .prepare(
            `${SELECT_CARD}
               JOIN cards_fts ON cards_fts.card_uid = c.card_uid
              WHERE cards_fts MATCH ?${gameClause} LIMIT ?`
          )
          .all(ftsQuery(nameText), ...gameParam, CANDIDATE_CAP) as CatalogCard[])
      );
    }
  }

  if (!found.length && number) {
    found.push(
      ...(db
        .prepare(
          `${SELECT_CARD}
             JOIN match_cards mc ON mc.card_uid = c.card_uid
            WHERE mc.number_norm = ?${gameClause} LIMIT ?`
        )
        .all(number, ...gameParam, CANDIDATE_CAP) as CatalogCard[])
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
      card.card_uid.toLowerCase() === wanted ||
      card.card_uid.toLowerCase().endsWith(`:${wanted}`)
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

export function resolveSetTokens(
  db: Database,
  tokens: string[],
  game?: string
): { token: string; setUids: string[] }[] {
  const resolved: { token: string; setUids: string[] }[] = [];
  const stmt = game
    ? db.prepare(
        "SELECT DISTINCT set_uid FROM match_sets WHERE token_norm = ? AND game = ? LIMIT 50"
      )
    : db.prepare("SELECT DISTINCT set_uid FROM match_sets WHERE token_norm = ? LIMIT 50");

  for (const token of tokens) {
    const norm = normalizeSetToken(token);
    if (!norm) continue;
    const rows = (
      game ? stmt.all(norm, game) : stmt.all(norm)
    ) as { set_uid: string }[];
    if (rows.length) {
      resolved.push({ token, setUids: rows.map((r) => r.set_uid) });
    }
  }

  return resolved;
}

function claimSetTokens(
  db: Database,
  tokens: string[],
  game?: string
): {
  resolvedSets: { token: string; setUids: string[] }[];
  remainingTokens: string[];
} {
  const resolvedSets: { token: string; setUids: string[] }[] = [];
  const claimed = new Set<string>();

  for (const phrase of contiguousPhrases(tokens)) {
    const words = phrase.split(" ");
    if (words.some((w) => claimed.has(w))) continue;

    const [match] = resolveSetTokens(db, [phrase], game);
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
