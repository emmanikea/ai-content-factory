import { NextResponse } from "next/server";

import { getGenerationContent } from "@/lib/generation/router";
import type { GenerationProvider } from "@/lib/generation/types";
import { getStore } from "@/lib/persistence/store";

const providers = new Set<GenerationProvider>(["openrouter", "comfyui"]);
const forwardedHeaders = [
  "content-type",
  "content-length",
  "content-range",
  "accept-ranges",
  "content-disposition",
] as const;

export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await context.params;
    const record = await getStore().getGeneration(id);
    if (!record) return NextResponse.json({ error: "generation not found" }, { status: 404 });
    if (record.status !== "completed") {
      return NextResponse.json({ error: `generation is ${record.status}, not completed` }, { status: 409 });
    }
    if (!record.providerJobId || !providers.has(record.provider as GenerationProvider)) {
      return NextResponse.json({ error: "generation does not have a retrievable provider output" }, { status: 409 });
    }

    const url = new URL(request.url);
    const parsedIndex = Number(url.searchParams.get("index") ?? 0);
    const index = Number.isInteger(parsedIndex) && parsedIndex >= 0 && parsedIndex <= 9 ? parsedIndex : 0;
    const upstream = await getGenerationContent(
      record.provider as GenerationProvider,
      record.providerJobId,
      index,
      request.headers.get("range") ?? undefined,
    );

    const headers = new Headers();
    for (const name of forwardedHeaders) {
      const value = upstream.headers.get(name);
      if (value) headers.set(name, value);
    }
    headers.set("Cache-Control", "private, no-store");

    return new Response(upstream.body, {
      status: upstream.status,
      headers,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to retrieve generated content" },
      { status: 502 },
    );
  }
}
