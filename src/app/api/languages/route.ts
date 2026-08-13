import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { countCards, listLanguages } from "@/lib/catalog";

export const dynamic = "force-dynamic";

export async function GET() {
  const db = getDb();
  return NextResponse.json({
    languages: listLanguages(db),
    totalCards: countCards(db),
  });
}
