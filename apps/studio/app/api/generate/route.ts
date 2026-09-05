import { NextResponse } from "next/server";

import { submitGeneration } from "@/lib/generation/router";
import type { GenerationRequest } from "@/lib/generation/types";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as GenerationRequest;

    if (!body.prompt?.trim()) {
      return NextResponse.json({ error: "prompt is required" }, { status: 400 });
    }

    const job = await submitGeneration({
      ...body,
      prompt: body.prompt.trim(),
    });

    return NextResponse.json(job, { status: 202 });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Generation failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
