import { NextResponse } from "next/server";
import fs from "node:fs";
import { resolveDbPath } from "@/lib/db";

/**
 * Liveness for Fly / Docker. Confirms the process is up and the catalog file
 * is present on the volume — does not open SQLite (so index rebuilds cannot
 * block the health check).
 */
export async function GET() {
  const dbPath = resolveDbPath();
  const dbPresent = fs.existsSync(dbPath);
  const status = dbPresent ? 200 : 503;
  return NextResponse.json(
    {
      ok: dbPresent,
      dbPath,
      dbPresent,
    },
    { status }
  );
}
