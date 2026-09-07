import { NextResponse } from "next/server";

import { getStore } from "@/lib/persistence/store";

export async function GET() {
  return NextResponse.json(await getStore().listProjects());
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const name = String(body.name ?? "").trim();
    if (!name) return NextResponse.json({ error: "name is required" }, { status: 400 });

    const row = await getStore().createProject({
      name,
      projectType: String(body.projectType ?? "social_video"),
      status: String(body.status ?? "active"),
      metadata: body.metadata ?? {},
    });

    return NextResponse.json(row, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Unable to create project" }, { status: 500 });
  }
}
