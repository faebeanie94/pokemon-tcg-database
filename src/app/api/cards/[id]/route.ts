import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { getCard } from "@/lib/catalog";

export const dynamic = "force-dynamic";

/**
 * One card by canonical UID, e.g. /api/cards/en:BS%234 for 'en:BS#4'. The UID
 * is stable across rebuilds, so it is safe for a grading record to store.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const cardUid = decodeURIComponent(id).trim();
  if (!cardUid) {
    return NextResponse.json({ error: "card id is required" }, { status: 400 });
  }

  const card = getCard(getDb(), cardUid);
  if (!card) {
    return NextResponse.json({ error: "card not found" }, { status: 404 });
  }
  return NextResponse.json({ card });
}
