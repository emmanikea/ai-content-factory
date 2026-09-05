import {
  GetObjectCommand,
  HeadObjectCommand,
  PutObjectCommand,
  S3Client,
} from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

let client: S3Client | undefined;

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is not configured`);
  return value;
}

function bucket() {
  return required("OBJECT_STORAGE_BUCKET");
}

function s3() {
  if (client) return client;

  const endpoint = process.env.OBJECT_STORAGE_ENDPOINT?.trim();
  client = new S3Client({
    region: process.env.OBJECT_STORAGE_REGION?.trim() || "auto",
    ...(endpoint ? { endpoint } : {}),
    forcePathStyle: process.env.OBJECT_STORAGE_FORCE_PATH_STYLE === "true",
    credentials: {
      accessKeyId: required("OBJECT_STORAGE_ACCESS_KEY_ID"),
      secretAccessKey: required("OBJECT_STORAGE_SECRET_ACCESS_KEY"),
    },
  });
  return client;
}

export function isObjectStorageConfigured() {
  return Boolean(
    process.env.OBJECT_STORAGE_BUCKET &&
      process.env.OBJECT_STORAGE_ACCESS_KEY_ID &&
      process.env.OBJECT_STORAGE_SECRET_ACCESS_KEY,
  );
}

function safePart(value: string) {
  return value
    .normalize("NFKD")
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120) || "asset";
}

function assertStorageKey(key: string) {
  if (!key || key.startsWith("/") || key.includes("..") || key.includes("\\")) {
    throw new Error("invalid object storage key");
  }
}

function publicUrl(key: string) {
  const base = process.env.OBJECT_STORAGE_PUBLIC_BASE_URL?.replace(/\/$/, "");
  if (!base) return undefined;
  return `${base}/${key.split("/").map(encodeURIComponent).join("/")}`;
}

export function createStorageKey(filename: string, namespace = "references") {
  const prefix = (process.env.OBJECT_STORAGE_PREFIX || "ai-content-factory")
    .split("/")
    .map(safePart)
    .filter(Boolean)
    .join("/");
  const stamp = new Date().toISOString().slice(0, 10);
  const id = crypto.randomUUID();
  return `${prefix}/${safePart(namespace)}/${stamp}/${id}-${safePart(filename)}`;
}

export async function createUploadUrl(input: {
  filename: string;
  contentType: string;
  namespace?: string;
  expiresInSeconds?: number;
}) {
  const storageKey = createStorageKey(input.filename, input.namespace);
  const expiresIn = Math.min(Math.max(input.expiresInSeconds ?? 900, 60), 3600);
  const command = new PutObjectCommand({
    Bucket: bucket(),
    Key: storageKey,
    ContentType: input.contentType,
  });
  const uploadUrl = await getSignedUrl(s3(), command, { expiresIn });
  return {
    storageKey,
    uploadUrl,
    headers: { "Content-Type": input.contentType },
    expiresAt: new Date(Date.now() + expiresIn * 1000).toISOString(),
  };
}

export async function createReadUrl(storageKey: string, expiresInSeconds = 900) {
  assertStorageKey(storageKey);
  const stablePublicUrl = publicUrl(storageKey);
  if (stablePublicUrl) return stablePublicUrl;

  const expiresIn = Math.min(Math.max(expiresInSeconds, 60), 3600);
  return getSignedUrl(
    s3(),
    new GetObjectCommand({ Bucket: bucket(), Key: storageKey }),
    { expiresIn },
  );
}

export async function objectExists(storageKey: string) {
  assertStorageKey(storageKey);
  try {
    await s3().send(new HeadObjectCommand({ Bucket: bucket(), Key: storageKey }));
    return true;
  } catch (error: any) {
    const status = error?.$metadata?.httpStatusCode;
    if (status === 404 || error?.name === "NotFound" || error?.name === "NoSuchKey") return false;
    throw error;
  }
}
