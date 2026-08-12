import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { createCard, listCards, ValidationError } from "@/lib/cards";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const search = searchParams.get("search") ?? undefined;
  const type = searchParams.get("type") ?? undefined;

  const cards = listCards(getDb(), { search, type });
  return NextResponse.json({ cards });
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }

  try {
    const input = body as Record<string, unknown>;
    const card = createCard(getDb(), {
      name: String(input.name ?? ""),
      set: String(input.set ?? ""),
      type: String(input.type ?? ""),
      rarity: String(input.rarity ?? ""),
      hp: input.hp === undefined || input.hp === null || input.hp === ""
        ? null
        : Number(input.hp),
    });
    return NextResponse.json({ card }, { status: 201 });
  } catch (err) {
    if (err instanceof ValidationError) {
      return NextResponse.json({ error: err.message }, { status: 400 });
    }
    throw err;
  }
}
