import { NextResponse } from "next/server";

import { getStore } from "@/lib/persistence/store";
import { createReadUrl, isObjectStorageConfigured } from "@/lib/storage/s3";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await context.params;
    const reference = await getStore().getReference(id);
    if (!reference) return NextResponse.json({ error: "reference not found" }, { status: 404 });

    if (isObjectStorageConfigured()) {
      const url = await createReadUrl(reference.storageKey, 300);
      return NextResponse.redirect(url);
    }

    if (reference.sourceUrl) {
      const url = new URL(reference.sourceUrl);
      if (url.protocol !== "https:") {
        return NextResponse.json({ error: "reference source URL must use HTTPS" }, { status: 409 });
      }
      return NextResponse.redirect(url);
    }

    return NextResponse.json(
      { error: "reference preview requires object storage or a source URL" },
      { status: 409 },
    );
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Could not load reference" },
      { status: 500 },
    );
  }
}
