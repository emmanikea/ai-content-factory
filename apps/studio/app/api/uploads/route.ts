import { NextResponse } from "next/server";

import { createUploadUrl, isObjectStorageConfigured } from "@/lib/storage/s3";

const namespaces = new Set(["references", "assets", "qa"]);
const allowedPrefixes = ["image/", "video/", "audio/"];

export async function POST(request: Request) {
  try {
    if (!isObjectStorageConfigured()) {
      return NextResponse.json({ error: "object storage is not configured" }, { status: 503 });
    }

    const body = await request.json();
    const filename = String(body.filename ?? "").trim();
    const contentType = String(body.contentType ?? "").trim().toLowerCase();
    const namespace = String(body.namespace ?? "references").trim();

    if (!filename || filename.length > 255) {
      return NextResponse.json({ error: "filename is required and must be 255 characters or fewer" }, { status: 400 });
    }
    if (!allowedPrefixes.some((prefix) => contentType.startsWith(prefix))) {
      return NextResponse.json({ error: "contentType must be image/*, video/*, or audio/*" }, { status: 400 });
    }
    if (!namespaces.has(namespace)) {
      return NextResponse.json({ error: "invalid upload namespace" }, { status: 400 });
    }

    return NextResponse.json(
      await createUploadUrl({ filename, contentType, namespace }),
      { status: 201 },
    );
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to create upload URL" },
      { status: 500 },
    );
  }
}
