import { NextResponse } from "next/server";

import { getStore } from "@/lib/persistence/store";
import type { ReferenceKind } from "@/lib/domain/types";

const kinds = new Set<ReferenceKind>(["image", "video", "audio", "performance", "location", "wardrobe"]);

export async function GET(request: Request) {
  const url = new URL(request.url);
  const characterId = url.searchParams.get("characterId") ?? undefined;
  return NextResponse.json(await getStore().listReferences(characterId));
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const kind = body.kind as ReferenceKind;
    const storageKey = String(body.storageKey ?? "").trim();
    if (!kinds.has(kind)) return NextResponse.json({ error: "invalid reference kind" }, { status: 400 });
    if (!storageKey) return NextResponse.json({ error: "storageKey is required" }, { status: 400 });

    const row = await getStore().addReference({
      characterId: body.characterId,
      kind,
      storageKey,
      sourceUrl: body.sourceUrl,
      label: body.label,
      consentVerified: Boolean(body.consentVerified),
      metadata: body.metadata ?? {},
    });

    return NextResponse.json(row, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Unable to add reference" }, { status: 500 });
  }
}
