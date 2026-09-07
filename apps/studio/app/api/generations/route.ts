import { NextResponse } from "next/server";

import { getStore } from "@/lib/persistence/store";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const parsed = Number(url.searchParams.get("limit") ?? 50);
  const limit = Number.isFinite(parsed) ? Math.min(Math.max(parsed, 1), 250) : 50;
  return NextResponse.json(await getStore().listGenerations(limit));
}
