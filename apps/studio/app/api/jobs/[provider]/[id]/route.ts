import { NextResponse } from "next/server";

import { getGeneration } from "@/lib/generation/router";
import type { GenerationProvider } from "@/lib/generation/types";

const validProviders = new Set<GenerationProvider>(["openrouter", "comfyui"]);

export async function GET(
  _request: Request,
  context: { params: Promise<{ provider: string; id: string }> },
) {
  try {
    const { provider, id } = await context.params;
    if (!validProviders.has(provider as GenerationProvider)) {
      return NextResponse.json({ error: "unknown provider" }, { status: 400 });
    }

    const job = await getGeneration(provider as GenerationProvider, id);
    return NextResponse.json(job);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not fetch job";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
