import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { searchCards } from "@/lib/catalog";

export const dynamic = "force-dynamic";

/**
 * Catalog search. Read-only: the catalog is loaded from the exported
 * workbooks by `pnpm import:catalog`, never written to over HTTP.
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);

  const limit = parseIntOr(searchParams.get("limit"), 50);
  const offset = parseIntOr(searchParams.get("offset"), 0);
  if (limit === null || offset === null) {
    return NextResponse.json(
      { error: "limit and offset must be integers" },
      { status: 400 }
    );
  }

  const result = searchCards(getDb(), {
    q: searchParams.get("q") ?? searchParams.get("search") ?? undefined,
    game: searchParams.get("game") ?? undefined,
    language: searchParams.get("language") ?? undefined,
    set: searchParams.get("set") ?? undefined,
    number: searchParams.get("number") ?? undefined,
    limit,
    offset,
  });

  return NextResponse.json(result);
}

function parseIntOr(value: string | null, fallback: number): number | null {
  if (value === null || value === "") return fallback;
  const parsed = Number(value);
  return Number.isInteger(parsed) ? parsed : null;
}
