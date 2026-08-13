import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { matchCards, type MatchRequest } from "@/lib/match";

export const dynamic = "force-dynamic";

/**
 * The endpoint the grading program calls: send what is known about a physical
 * card, get back the catalog rows it could be, ranked, with the reasons each
 * one scored and whether the top hit is decisive enough to accept without a
 * human looking at it.
 */
export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }

  const input = (body ?? {}) as Record<string, unknown>;
  const printedTotal = input.printedTotal ?? input.printed_total;

  if (printedTotal !== undefined && printedTotal !== null && printedTotal !== "") {
    const parsed = Number(printedTotal);
    if (!Number.isInteger(parsed)) {
      return NextResponse.json(
        { error: "printedTotal must be an integer" },
        { status: 400 }
      );
    }
  }

  const matchRequest: MatchRequest = {
    query: asString(input.query),
    name: asString(input.name),
    language: asString(input.language),
    game: asString(input.game),
    set: asString(input.set),
    number: asString(input.number),
    cardId: asString(input.cardId ?? input.card_id),
    parallel: asString(input.parallel),
    subject: asString(input.subject ?? input.subjectName ?? input.subject_name),
    sports: input.sports === true || asString(input.game) === "sports",
    printedTotal: printedTotal ? Number(printedTotal) : undefined,
    limit: input.limit === undefined ? undefined : Number(input.limit),
  };

  const hasSomethingToMatchOn = [
    matchRequest.query,
    matchRequest.name,
    matchRequest.set,
    matchRequest.number,
    matchRequest.cardId,
    matchRequest.subject,
  ].some((v) => v && v.trim());

  if (!hasSomethingToMatchOn) {
    return NextResponse.json(
      {
        error:
          "provide at least one of: query, name, set, number, cardId, subject",
      },
      { status: 400 }
    );
  }

  return NextResponse.json(matchCards(getDb(), matchRequest));
}

/** Convenience for quick checks from a browser or shell: /api/match?q=... */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get("q") ?? searchParams.get("query");
  const set = searchParams.get("set") ?? undefined;
  const name = searchParams.get("name") ?? undefined;
  const number = searchParams.get("number") ?? undefined;
  const game = searchParams.get("game") ?? undefined;

  if (!query?.trim() && !(set && name && number)) {
    return NextResponse.json(
      { error: "q is required, or provide set+name+number" },
      { status: 400 }
    );
  }

  return NextResponse.json(
    matchCards(getDb(), {
      query: query ?? undefined,
      set,
      name,
      number,
      game,
      sports: game === "sports",
      language: searchParams.get("language") ?? undefined,
      limit: searchParams.get("limit")
        ? Number(searchParams.get("limit"))
        : undefined,
    })
  );
}

function asString(value: unknown): string | undefined {
  if (value === undefined || value === null) return undefined;
  const text = String(value);
  return text.trim() ? text : undefined;
}
