"use client";

import { useCallback, useEffect, useState } from "react";
import type { CatalogCard } from "@/lib/catalog";
import type { MatchResponse } from "@/lib/match";

/**
 * Operator console for the grading workflow: type what is printed on the card,
 * see the catalog rows it could be. The same /api/match endpoint the grading
 * program calls backs this page, so what an operator sees here is what the
 * program gets.
 */

interface LanguageOption {
  language: string;
  card_count: number;
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

const EXAMPLES = ["Charizard 4/102", "BS 4", "base1-4", "SV1a 001", "リザードン"];

export default function Home() {
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState("");
  const [languages, setLanguages] = useState<LanguageOption[]>([]);
  const [totalCards, setTotalCards] = useState<number | null>(null);
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/languages")
      .then((res) => res.json())
      .then((data) => {
        setLanguages(data.languages ?? []);
        setTotalCards(data.totalCards ?? 0);
      })
      .catch(() => setError("Could not load catalog languages."));
  }, []);

  const runMatch = useCallback(async () => {
    if (!query.trim()) {
      setResult(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, language: language || undefined, limit: 25 }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "Match failed.");
        setResult(null);
        return;
      }
      setResult(data as MatchResponse);
    } catch {
      setError("Match request failed.");
    } finally {
      setLoading(false);
    }
  }, [query, language]);

  useEffect(() => {
    const timer = setTimeout(runMatch, 250);
    return () => clearTimeout(timer);
  }, [runMatch]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-black tracking-tight text-pokeblueDark">
          Card lookup
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Identify a card from what is printed on it: name, collector number,
          set code, or a source card ID.
          {totalCards !== null && (
            <> {totalCards.toLocaleString()} printings in the catalog.</>
          )}
        </p>
      </header>

      <section className="mb-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-[1fr_240px]">
        <div>
          <label
            htmlFor="lookup"
            className="mb-1 block text-sm font-medium text-slate-600"
          >
            Card
          </label>
          <input
            id="lookup"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Charizard 4/102"
            className="w-full rounded-lg border border-slate-300 px-4 py-2.5 outline-none focus:border-pokeblue focus:ring-2 focus:ring-pokeblue/30"
          />
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

        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 md:col-span-2">
          <span>Try:</span>
          {EXAMPLES.map((example) => (
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
      </section>

      {error && (
        <p className="mb-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </p>
      )}

      {result && <Interpretation result={result} loading={loading} />}

      {result && result.candidates.length > 0 && (
        <ol className="space-y-2">
          {result.candidates.map((candidate, index) => (
            <CandidateRow
              key={candidate.card.id}
              card={candidate.card}
              score={candidate.score}
              matchedOn={candidate.matchedOn}
              best={index === 0 && result.unambiguous}
            />
          ))}
        </ol>
      )}

      {result && result.candidates.length === 0 && !loading && (
        <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-slate-400">
          Nothing in the catalog matches that.
        </p>
      )}
    </main>
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
  if (read.cardId) parts.push(`card ID ${read.cardId}`);
  if (read.name) parts.push(`name "${read.name}"`);
  if (read.number) parts.push(`number ${read.number}`);
  if (read.printedTotal) parts.push(`printed total ${read.printedTotal}`);
  for (const set of read.sets) {
    parts.push(
      `set "${set.token}" (${set.setIds.length} ${
        set.setIds.length === 1 ? "set" : "sets"
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

function CandidateRow({
  card,
  score,
  matchedOn,
  best,
}: {
  card: CatalogCard;
  score: number;
  matchedOn: string[];
  best: boolean;
}) {
  return (
    <li
      className={`rounded-xl border bg-white p-4 shadow-sm ${
        best ? "border-emerald-300 ring-1 ring-emerald-200" : "border-slate-200"
      }`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <span className="font-bold text-slate-800">{card.name}</span>
          {card.english_name && card.english_name !== card.name && (
            <span className="ml-2 text-sm text-slate-500">
              {card.english_name}
            </span>
          )}
        </div>
        <span className="text-xs font-semibold text-slate-400">score {score}</span>
      </div>

      <div className="mt-1 text-sm text-slate-600">
        <span className="font-medium">{card.set_name}</span>
        {card.set_abbreviation && (
          <span className="text-slate-400"> ({card.set_abbreviation})</span>
        )}
        <span className="text-slate-400"> · </span>
        <span>
          #{card.card_number}
          {card.printed_total ? `/${card.printed_total}` : ""}
        </span>
        <span className="text-slate-400"> · </span>
        <span className="uppercase">{card.language}</span>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <code className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">
          {card.source}:{card.source_card_id}
        </code>
        {matchedOn.map((reason) => (
          <span
            key={reason}
            className="rounded-full border border-slate-200 px-2 py-0.5 text-slate-500"
          >
            {reason}
          </span>
        ))}
      </div>
    </li>
  );
}
