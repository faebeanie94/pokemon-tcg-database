import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { listSets } from "@/lib/catalog";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const sets = listSets(getDb(), {
    language: searchParams.get("language") ?? undefined,
    q: searchParams.get("q") ?? undefined,
    limit: searchParams.get("limit") ? Number(searchParams.get("limit")) : undefined,
  });
  return NextResponse.json({ sets });
}
