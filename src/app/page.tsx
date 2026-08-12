"use client";

import { useCallback, useEffect, useState } from "react";
import type { Card } from "@/lib/cards";
import { CARD_TYPES, RARITIES } from "@/lib/cards";
import { typeColor } from "@/lib/typeColors";

interface FormState {
  name: string;
  set: string;
  type: string;
  rarity: string;
  hp: string;
}

const EMPTY_FORM: FormState = {
  name: "",
  set: "",
  type: "Colorless",
  rarity: "Common",
  hp: "",
};

export default function Home() {
  const [cards, setCards] = useState<Card[]>([]);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchCards = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (typeFilter) params.set("type", typeFilter);
    const res = await fetch(`/api/cards?${params.toString()}`);
    const data = await res.json();
    setCards(data.cards ?? []);
    setLoading(false);
  }, [search, typeFilter]);

  useEffect(() => {
    const timer = setTimeout(fetchCards, 200);
    return () => clearTimeout(timer);
  }, [fetchCards]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    const res = await fetch("/api/cards", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    const data = await res.json();
    setSubmitting(false);
    if (!res.ok) {
      setFormError(data.error ?? "Something went wrong");
      return;
    }
    setForm(EMPTY_FORM);
    await fetchCards();
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <header className="mb-8 flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-full border-4 border-pokeblueDark bg-pokeyellow text-2xl">
          ⚡
        </div>
        <div>
          <h1 className="text-3xl font-black tracking-tight text-pokeblueDark">
            Pokémon TCG Database
          </h1>
          <p className="text-sm text-slate-500">
            Browse, search, and catalog your Trading Card Game collection.
          </p>
        </div>
      </header>

      <section className="mb-8 grid gap-4 rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm md:grid-cols-[1fr_auto]">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by card name or set…"
          aria-label="Search cards"
          className="w-full rounded-lg border border-slate-300 px-4 py-2.5 outline-none focus:border-pokeblue focus:ring-2 focus:ring-pokeblue/30"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          aria-label="Filter by type"
          className="rounded-lg border border-slate-300 px-4 py-2.5 outline-none focus:border-pokeblue"
        >
          <option value="">All types</option>
          {CARD_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </section>

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-700">
              Cards{" "}
              <span className="text-sm font-normal text-slate-400">
                ({cards.length})
              </span>
            </h2>
          </div>

          {loading ? (
            <p className="text-slate-400">Loading…</p>
          ) : cards.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-slate-400">
              No cards match your search.
            </p>
          ) : (
            <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {cards.map((card) => (
                <li
                  key={card.id}
                  data-testid="card-item"
                  className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                >
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <h3 className="font-bold text-slate-800">{card.name}</h3>
                    {card.hp != null && (
                      <span className="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-600">
                        {card.hp} HP
                      </span>
                    )}
                  </div>
                  <p className="mb-3 text-sm text-slate-500">{card.set}</p>
                  <div className="flex flex-wrap gap-2">
                    <span
                      className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${typeColor(
                        card.type
                      )}`}
                    >
                      {card.type}
                    </span>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                      {card.rarity}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-bold text-slate-700">Add a card</h2>
          <form onSubmit={handleSubmit} className="space-y-3">
            <Field label="Name">
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="input"
                placeholder="e.g. Gengar"
              />
            </Field>
            <Field label="Set">
              <input
                required
                value={form.set}
                onChange={(e) => setForm({ ...form, set: e.target.value })}
                className="input"
                placeholder="e.g. Fossil"
              />
            </Field>
            <Field label="Type">
              <select
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}
                className="input"
              >
                {CARD_TYPES.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </Field>
            <Field label="Rarity">
              <select
                value={form.rarity}
                onChange={(e) => setForm({ ...form, rarity: e.target.value })}
                className="input"
              >
                {RARITIES.map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </Field>
            <Field label="HP (optional)">
              <input
                type="number"
                min={0}
                value={form.hp}
                onChange={(e) => setForm({ ...form, hp: e.target.value })}
                className="input"
                placeholder="e.g. 60"
              />
            </Field>

            {formError && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {formError}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-pokeblue px-4 py-2.5 font-semibold text-white transition hover:bg-pokeblueDark disabled:opacity-60"
            >
              {submitting ? "Adding…" : "Add card"}
            </button>
          </form>
        </aside>
      </div>

      <style jsx>{`
        :global(.input) {
          width: 100%;
          border-radius: 0.5rem;
          border: 1px solid rgb(203 213 225);
          padding: 0.5rem 0.75rem;
          outline: none;
        }
        :global(.input:focus) {
          border-color: #3d7dca;
          box-shadow: 0 0 0 2px rgba(61, 125, 202, 0.25);
        }
      `}</style>
    </main>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-600">
        {label}
      </span>
      {children}
    </label>
  );
}
