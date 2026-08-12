import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { getCard } from "@/lib/cards";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const numericId = Number(id);
  if (!Number.isInteger(numericId)) {
    return NextResponse.json({ error: "invalid id" }, { status: 400 });
  }

  const card = getCard(getDb(), numericId);
  if (!card) {
    return NextResponse.json({ error: "card not found" }, { status: 404 });
  }
  return NextResponse.json({ card });
}
