import { NextResponse } from "next/server";

import { getStore } from "@/lib/persistence/store";
import type { CharacterKind, ConsentStatus } from "@/lib/domain/types";

const kinds = new Set<CharacterKind>(["real_person", "synthetic", "brand_mascot"]);
const consentStates = new Set<ConsentStatus>(["not_required", "pending", "verified", "revoked"]);

export async function GET() {
  return NextResponse.json(await getStore().listCharacters());
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const name = String(body.name ?? "").trim();
    const slug = String(body.slug ?? "").trim().toLowerCase();
    const kind = body.kind as CharacterKind;
    const consentStatus = (body.consentStatus ?? (kind === "real_person" ? "pending" : "not_required")) as ConsentStatus;

    if (!name || !slug) return NextResponse.json({ error: "name and slug are required" }, { status: 400 });
    if (!kinds.has(kind)) return NextResponse.json({ error: "invalid character kind" }, { status: 400 });
    if (!consentStates.has(consentStatus)) return NextResponse.json({ error: "invalid consent status" }, { status: 400 });
    if (kind === "real_person" && consentStatus === "not_required") {
      return NextResponse.json(
        { error: "real-person characters require pending, verified, or revoked consent status" },
        { status: 400 },
      );
    }

    const character = await getStore().createCharacter({
      name,
      slug,
      kind,
      description: body.description,
      voiceProfileId: body.voiceProfileId,
      consentStatus,
      consentNotes: body.consentNotes,
      metadata: body.metadata ?? {},
    });

    return NextResponse.json(character, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Unable to create character" }, { status: 500 });
  }
}
