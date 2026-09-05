import { NextResponse } from "next/server";

import type { CharacterKind, ConsentStatus } from "@/lib/domain/types";
import { getStore } from "@/lib/persistence/store";

const kinds = new Set<CharacterKind>(["real_person", "synthetic", "brand_mascot"]);
const consentStates = new Set<ConsentStatus>(["not_required", "pending", "verified", "revoked"]);

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const character = await getStore().getCharacter(id);
  return character
    ? NextResponse.json(character)
    : NextResponse.json({ error: "character not found" }, { status: 404 });
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await context.params;
    const store = getStore();
    const existing = await store.getCharacter(id);
    if (!existing) return NextResponse.json({ error: "character not found" }, { status: 404 });

    const body = await request.json();
    const kind = (body.kind ?? existing.kind) as CharacterKind;
    const consentStatus = (body.consentStatus ?? existing.consentStatus) as ConsentStatus;
    if (!kinds.has(kind)) return NextResponse.json({ error: "invalid character kind" }, { status: 400 });
    if (!consentStates.has(consentStatus)) return NextResponse.json({ error: "invalid consent status" }, { status: 400 });
    if (kind === "real_person" && consentStatus === "not_required") {
      return NextResponse.json(
        { error: "real-person characters cannot use consent_status=not_required" },
        { status: 400 },
      );
    }

    const name = body.name === undefined ? existing.name : String(body.name).trim();
    const slug = body.slug === undefined ? existing.slug : String(body.slug).trim().toLowerCase();
    if (!name || !slug) return NextResponse.json({ error: "name and slug cannot be empty" }, { status: 400 });

    const updated = await store.updateCharacter(id, {
      name,
      slug,
      kind,
      consentStatus,
      description: body.description === undefined ? existing.description : body.description,
      voiceProfileId: body.voiceProfileId === undefined ? existing.voiceProfileId : body.voiceProfileId,
      consentNotes: body.consentNotes === undefined ? existing.consentNotes : body.consentNotes,
      metadata: body.metadata === undefined ? existing.metadata : body.metadata,
    });

    return NextResponse.json(updated);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to update character" },
      { status: 500 },
    );
  }
}
