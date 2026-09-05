import { NextResponse } from "next/server";

import { getStore } from "@/lib/persistence/store";
import type { ReferenceKind } from "@/lib/domain/types";
import { isObjectStorageConfigured, objectExists } from "@/lib/storage/s3";

const kinds = new Set<ReferenceKind>(["image", "video", "audio", "performance", "location", "wardrobe"]);

function httpsUrl(value: unknown) {
  if (!value) return undefined;
  const url = new URL(String(value));
  if (url.protocol !== "https:") throw new Error("sourceUrl must use HTTPS");
  return url.toString();
}

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
    const characterId = body.characterId ? String(body.characterId) : undefined;
    const sourceUrl = httpsUrl(body.sourceUrl);
    if (!kinds.has(kind)) return NextResponse.json({ error: "invalid reference kind" }, { status: 400 });
    if (!storageKey) return NextResponse.json({ error: "storageKey is required" }, { status: 400 });

    if (isObjectStorageConfigured()) {
      const exists = await objectExists(storageKey);
      if (!exists && !sourceUrl) {
        return NextResponse.json(
          { error: "uploaded object was not found; complete the signed upload before registering the reference" },
          { status: 409 },
        );
      }
    }

    const store = getStore();
    const character = characterId ? await store.getCharacter(characterId) : undefined;
    if (characterId && !character) {
      return NextResponse.json({ error: "character not found" }, { status: 404 });
    }

    const requestedConsentVerified = Boolean(body.consentVerified);
    const consentVerified = character?.kind === "real_person"
      ? requestedConsentVerified && character.consentStatus === "verified"
      : requestedConsentVerified;

    const row = await store.addReference({
      characterId,
      kind,
      storageKey,
      sourceUrl,
      label: body.label,
      consentVerified,
      metadata: body.metadata ?? {},
    });

    return NextResponse.json(row, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Unable to add reference" }, { status: 500 });
  }
}
