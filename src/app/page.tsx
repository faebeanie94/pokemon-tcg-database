"use client";

import { useCallback, useEffect, useState } from "react";
import type { CatalogCard } from "@/lib/catalog";
import type { MatchResponse } from "@/lib/match";

/**
 * Operator console for the grading workflow, in two modes.
 *
 * Identify takes what is printed on a card and ranks the catalog rows it could
 * be, through the same /api/match endpoint the grading program calls. Browse
 * pages through the catalog for the times a card has to be found by working
 * through a set instead.
 *
 * Sports mode uses Set / Subject / Parallel / Number (serial is optional
 * interpretation only) instead of a single free-text query.
 */

type Mode = "identify" | "browse";

interface LanguageOption {
  language: string;
  card_count: number;
}

interface GameOption {
  game: string;
  name: string;
  kind: string;
  card_count: number;
}

interface SearchResponse {
  cards: CatalogCard[];
  total: number;
  limit: number;
  offset: number;
}

const LANGUAGE_NAMES: Record<string, string> = {
  en: "English",
  fr: "French",
  es: "Spanish",
  it: "Italian",
  pt: "Portuguese",
  "pt-br": "Portuguese (Brazil)",
  de: "German",
  ja: "Japanese",
  ko: "Korean",
  "zh-tw": "Chinese (Traditional)",
  "zh-cn": "Chinese (Simplified)",
  id: "Indonesian",
  th: "Thai",
};

const TCG_EXAMPLES = ["Charizard 4/102", "BS 4", "base1-4", "SV1a 001", "リザードン"];
const SPORTS_EXAMPLES = [
  {
    label: "Beckham Halo Ref",
    set: "2025-26 TOPPS MANCHESTER UNITED TEAM SET",
    subject: "SIR DAVID BECKHAM",
    parallel: "HALO REF",
    number: "38",
  },
  {
    label: "Michaels Ruby /15",
    set: "2024 PANINI FLAWLESS WWE",
    subject: "SHAWN MICHAELS",
    parallel: "RUBY REF",
    number: "SSL-SM",
    serial: "09/15",
  },
];

const PAGE_SIZE = 25;

export default function Home() {
  const [mode, setMode] = useState<Mode>("identify");
  const [query, setQuery] = useState("");
  const [game, setGame] = useState("");
  const [language, setLanguage] = useState("");
  const [setFilter, setSetFilter] = useState("");
  const [numberFilter, setNumberFilter] = useState("");
  const [sportsSet, setSportsSet] = useState("");
  const [sportsSubject, setSportsSubject] = useState("");
  const [sportsParallel, setSportsParallel] = useState("");
  const [sportsNumber, setSportsNumber] = useState("");
  const [sportsSerial, setSportsSerial] = useState("");
  const [offset, setOffset] = useState(0);

  const [languages, setLanguages] = useState<LanguageOption[]>([]);
  const [games, setGames] = useState<GameOption[]>([]);
  const [totalCards, setTotalCards] = useState<number | null>(null);
  const [match, setMatch] = useState<MatchResponse | null>(null);
  const [search, setSearch] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sportsMode = game === "sports";

  useEffect(() => {
    fetch("/api/languages")
      .then((res) => res.json())
      .then((data) => {
        setLanguages(data.languages ?? []);
        setTotalCards(data.totalCards ?? 0);
        setGames(data.games ?? []);
      })
      .catch(() => setError("Could not load catalog languages."));
  }, []);

  useEffect(() => {
    setOffset(0);
  }, [
    mode,
    query,
    game,
    language,
    setFilter,
    numberFilter,
    sportsSet,
    sportsSubject,
    sportsParallel,
    sportsNumber,
    sportsSerial,
  ]);

  const runMatch = useCallback(async () => {
    if (sportsMode) {
      if (
        !sportsSet.trim() &&
        !sportsSubject.trim() &&
        !sportsParallel.trim() &&
        !sportsNumber.trim()
      ) {
        setMatch(null);
        return;
      }
    } else if (!query.trim()) {
      setMatch(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const body = sportsMode
        ? {
            game: "sports",
            sports: true,
            set: sportsSet || undefined,
            subject: sportsSubject || undefined,
            parallel: sportsParallel || undefined,
            number: sportsNumber || undefined,
            serial: sportsSerial || undefined,
            language: language || undefined,
            limit: 25,
          }
        : {
            query,
            game: game || undefined,
            language: language || undefined,
            limit: 25,
          };
      const res = await fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "Match failed.");
        setMatch(null);
        return;
      }
      setMatch(data as MatchResponse);
    } catch {
      setError("Match request failed.");
    } finally {
      setLoading(false);
    }
  }, [
    query,
    language,
    game,
    sportsMode,
    sportsSet,
    sportsSubject,
    sportsParallel,
    sportsNumber,
    sportsSerial,
  ]);

  const runSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(offset),
    });
    if (query.trim()) params.set("q", query.trim());
    if (game) params.set("game", game);
    if (language) params.set("language", language);
    if (setFilter.trim()) params.set("set", setFilter.trim());
    if (numberFilter.trim()) params.set("number", numberFilter.trim());

    try {
      const res = await fetch(`/api/cards?${params.toString()}`);
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "Search failed.");
        setSearch(null);
        return;
      }
      setSearch(data as SearchResponse);
    } catch {
      setError("Search request failed.");
    } finally {
      setLoading(false);
    }
  }, [query, game, language, setFilter, numberFilter, offset]);

  useEffect(() => {
    if (mode !== "identify") return;
    const timer = setTimeout(runMatch, 250);
    return () => clearTimeout(timer);
  }, [mode, runMatch]);

  useEffect(() => {
    if (mode !== "browse") return;
    const timer = setTimeout(runSearch, 250);
    return () => clearTimeout(timer);
  }, [mode, runSearch]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <header className="mb-6">
        <h1 className="text-2xl font-black tracking-tight text-pokeblueDark">
          Card lookup
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Identify a card from what is printed on it.
          {totalCards !== null && (
            <> {totalCards.toLocaleString()} printings in the catalog.</>
          )}
        </p>
      </header>

      <div className="mb-4 inline-flex rounded-lg border border-slate-200 bg-white p-1 text-sm shadow-sm">
        <ModeButton current={mode} value="identify" onSelect={setMode}>
          Identify a card
        </ModeButton>
        <ModeButton current={mode} value="browse" onSelect={setMode}>
          Browse the catalog
        </ModeButton>
      </div>

      <section className="mb-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2">
        <div>
          <label htmlFor="game" className="mb-1 block text-sm font-medium text-slate-600">
            Game
          </label>
          <select
            id="game"
            value={game}
            onChange={(e) => setGame(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-4 py-2.5 outline-none focus:border-pokeblue"
          >
            <option value="">Any game</option>
            {games.map((g) => (
              <option key={g.game} value={g.game}>
                {g.name} ({g.card_count.toLocaleString()})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label
            htmlFor="language"
            className="mb-1 block text-sm font-medium text-slate-600"
          >
            Language
          </label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-4 py-2.5 outline-none focus:border-pokeblue"
          >
            <option value="">Any language</option>
            {languages.map((l) => (
              <option key={l.language} value={l.language}>
                {LANGUAGE_NAMES[l.language] ?? l.language} (
                {l.card_count.toLocaleString()})
              </option>
            ))}
          </select>
        </div>

        {mode === "identify" && sportsMode ? (
          <>
            <Field
              id="sports-set"
              label="Set name"
              value={sportsSet}
              onChange={setSportsSet}
              placeholder="2025-26 TOPPS MANCHESTER UNITED TEAM SET"
              autoFocus
            />
            <Field
              id="sports-subject"
              label="Subject"
              value={sportsSubject}
              onChange={setSportsSubject}
              placeholder="SIR DAVID BECKHAM"
            />
            <Field
              id="sports-parallel"
              label="Parallel"
              value={sportsParallel}
              onChange={setSportsParallel}
              placeholder="HALO REF"
            />
            <Field
              id="sports-number"
              label="Number"
              value={sportsNumber}
              onChange={setSportsNumber}
              placeholder="38 or SSL-SM"
            />
            <Field
              id="sports-serial"
              label="Serial (optional)"
              value={sportsSerial}
              onChange={setSportsSerial}
              placeholder="09/15"
            />
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 md:col-span-2">
              <span>Try:</span>
              {SPORTS_EXAMPLES.map((example) => (
                <button
                  key={example.label}
                  type="button"
                  onClick={() => {
                    setSportsSet(example.set);
                    setSportsSubject(example.subject);
                    setSportsParallel(example.parallel);
                    setSportsNumber(example.number);
                    setSportsSerial(example.serial ?? "");
                  }}
                  className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-medium text-slate-600 transition hover:border-pokeblue hover:text-pokeblue"
                >
                  {example.label}
                </button>
              ))}
            </div>
          </>
        ) : (
          <>
            <Field
              id="lookup"
              label={mode === "identify" ? "Card" : "Name or set"}
              value={query}
              onChange={setQuery}
              placeholder={mode === "identify" ? "Charizard 4/102" : "Charizard"}
              autoFocus
            />
            {mode === "browse" && (
              <>
                <Field
                  id="set"
                  label="Set (code, ID or name)"
                  value={setFilter}
                  onChange={setSetFilter}
                  placeholder="BS"
                />
                <Field
                  id="number"
                  label="Collector number"
                  value={numberFilter}
                  onChange={setNumberFilter}
                  placeholder="4"
                />
              </>
            )}
            {mode === "identify" && !sportsMode && (
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 md:col-span-2">
                <span>Try:</span>
                {TCG_EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => setQuery(example)}
                    className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-medium text-slate-600 transition hover:border-pokeblue hover:text-pokeblue"
                  >
                    {example}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </section>

      {error && (
        <p className="mb-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </p>
      )}

      {mode === "identify" ? (
        <IdentifyResults result={match} loading={loading} />
      ) : (
        <BrowseResults
          result={search}
          loading={loading}
          onPage={(next) => setOffset(next)}
        />
      )}
    </main>
  );
}

function ModeButton({
  current,
  value,
  onSelect,
  children,
}: {
  current: Mode;
  value: Mode;
  onSelect: (mode: Mode) => void;
  children: React.ReactNode;
}) {
  const active = current === value;
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      aria-pressed={active}
      className={`rounded-md px-3 py-1.5 font-medium transition ${
        active
          ? "bg-pokeblue text-white"
          : "text-slate-600 hover:text-pokeblueDark"
      }`}
    >
      {children}
    </button>
  );
}

function Field({
  id,
  label,
  value,
  onChange,
  placeholder,
  autoFocus,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-600">
        {label}
      </label>
      <input
        id={id}
        autoFocus={autoFocus}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-slate-300 px-4 py-2.5 outline-none focus:border-pokeblue focus:ring-2 focus:ring-pokeblue/30"
      />
    </div>
  );
}

function IdentifyResults({
  result,
  loading,
}: {
  result: MatchResponse | null;
  loading: boolean;
}) {
  if (!result) return null;

  return (
    <>
      <Interpretation result={result} loading={loading} />

      {result.candidates.length > 0 ? (
        <ol className="space-y-2">
          {result.candidates.map((candidate, index) => (
            <li
              key={candidate.card.card_uid}
              className={`rounded-xl border bg-white p-4 shadow-sm ${
                index === 0 && result.unambiguous
                  ? "border-emerald-300 ring-1 ring-emerald-200"
                  : "border-slate-200"
              }`}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <CardNames card={candidate.card} />
                <span className="text-xs font-semibold text-slate-400">
                  score {candidate.score}
                </span>
              </div>
              <CardLocation card={candidate.card} />
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                <SourceId card={candidate.card} />
                {candidate.matchedOn.map((reason) => (
                  <span
                    key={reason}
                    className="rounded-full border border-slate-200 px-2 py-0.5 text-slate-500"
                  >
                    {reason}
                  </span>
                ))}
              </div>
            </li>
          ))}
        </ol>
      ) : (
        !loading && <Empty>Nothing in the catalog matches that.</Empty>
      )}
    </>
  );
}

function BrowseResults({
  result,
  loading,
  onPage,
}: {
  result: SearchResponse | null;
  loading: boolean;
  onPage: (offset: number) => void;
}) {
  if (!result) return null;

  const { cards, total, limit, offset } = result;
  const first = total === 0 ? 0 : offset + 1;
  const last = Math.min(offset + limit, total);

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="text-slate-500">
          {total === 0
            ? "No cards match those filters."
            : `Showing ${first.toLocaleString()}–${last.toLocaleString()} of ${total.toLocaleString()}`}
          {loading && <span className="ml-2 text-slate-400">searching…</span>}
        </span>
        <div className="flex items-center gap-2">
          <PageButton disabled={offset === 0} onClick={() => onPage(Math.max(offset - limit, 0))}>
            Previous
          </PageButton>
          <PageButton disabled={last >= total} onClick={() => onPage(offset + limit)}>
            Next
          </PageButton>
        </div>
      </div>

      {cards.length > 0 ? (
        <ul className="space-y-2">
          {cards.map((card) => (
            <li
              key={card.card_uid}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <CardNames card={card} />
                <SourceId card={card} />
              </div>
              <CardLocation card={card} />
            </li>
          ))}
        </ul>
      ) : (
        !loading && <Empty>No cards match those filters.</Empty>
      )}
    </>
  );
}

function PageButton({
  disabled,
  onClick,
  children,
}: {
  disabled: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-medium text-slate-600 transition hover:border-pokeblue hover:text-pokeblue disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-slate-300 disabled:hover:text-slate-600"
    >
      {children}
    </button>
  );
}

function Interpretation({
  result,
  loading,
}: {
  result: MatchResponse;
  loading: boolean;
}) {
  const { interpretation: read } = result;
  const parts: string[] = [];
  if (read.game) parts.push(`game ${read.game}`);
  if (read.cardId) parts.push(`card ID ${read.cardId}`);
  if (read.subject) parts.push(`subject "${read.subject}"`);
  if (read.parallel) parts.push(`parallel "${read.parallel}"`);
  if (read.name) parts.push(`name "${read.name}"`);
  if (read.number) parts.push(`number ${read.number}`);
  if (read.serial_number && read.print_run) {
    parts.push(`serial ${read.serial_number}/${read.print_run}`);
  }
  if (read.printedTotal) parts.push(`printed total ${read.printedTotal}`);
  for (const set of read.sets) {
    parts.push(
      `set "${set.token}" (${set.setUids.length} ${
        set.setUids.length === 1 ? "set" : "sets"
      })`
    );
  }

  return (
    <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      <span className="text-slate-500">
        Read as: {parts.length ? parts.join(", ") : "free text"}
      </span>
      {loading && <span className="text-slate-400">searching…</span>}
      {!loading && (
        <span
          className={
            result.unambiguous
              ? "rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700"
              : "rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700"
          }
        >
          {result.unambiguous ? "single confident match" : "needs a decision"}
        </span>
      )}
    </div>
  );
}

function CardNames({ card }: { card: CatalogCard }) {
  const title = card.display_name || card.name;
  return (
    <div>
      <span className="font-bold text-slate-800">{title}</span>
      {card.english_name && card.english_name !== title && (
        <span className="ml-2 text-sm text-slate-500">{card.english_name}</span>
      )}
      {card.parallel && (
        <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
          {card.parallel}
        </span>
      )}
    </div>
  );
}

function CardLocation({ card }: { card: CatalogCard }) {
  return (
    <div className="mt-1 text-sm text-slate-600">
      <span className="mr-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs uppercase text-slate-500">
        {card.game}
      </span>
      <span className="font-medium">{card.set_name}</span>
      {card.set_code && (
        <span className="text-slate-400"> ({card.set_code})</span>
      )}
      {card.manufacturer && (
        <span className="text-slate-400"> · {card.manufacturer}</span>
      )}
      <span className="text-slate-400"> · </span>
      <span>
        #{card.card_number}
        {card.printed_total ? `/${card.printed_total}` : ""}
      </span>
      {card.serial_number && card.print_run && (
        <>
          <span className="text-slate-400"> · </span>
          <span>
            {card.serial_number}/{card.print_run}
          </span>
        </>
      )}
      <span className="text-slate-400"> · </span>
      <span className="uppercase">{card.language}</span>
    </div>
  );
}

function SourceId({ card }: { card: CatalogCard }) {
  return (
    <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
      {card.card_uid}
    </code>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-slate-400">
      {children}
    </p>
  );
}
