import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { listGames } from "@/lib/catalog";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({ games: listGames(getDb()) });
}
