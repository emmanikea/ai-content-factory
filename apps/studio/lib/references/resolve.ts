import type { CharacterReference } from "@/lib/domain/types";
import type { ContentFactoryStore } from "@/lib/persistence/store";
import {
  createReadUrl,
  isObjectStorageConfigured,
  objectExists,
} from "@/lib/storage/s3";

function publicHttps(url: string | undefined) {
  if (!url) return undefined;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" ? parsed.toString() : undefined;
  } catch {
    return undefined;
  }
}

async function assertReferenceConsent(
  reference: CharacterReference,
  store: ContentFactoryStore,
  selectedCharacterId?: string,
) {
  if (reference.characterId && selectedCharacterId && reference.characterId !== selectedCharacterId) {
    throw new Error(`reference ${reference.id} belongs to a different character`);
  }
  if (!reference.characterId) return;

  const character = await store.getCharacter(reference.characterId);
  if (!character) throw new Error(`reference ${reference.id} points to a missing character`);
  if (
    character.kind === "real_person" &&
    (character.consentStatus !== "verified" || !reference.consentVerified)
  ) {
    throw new Error(`reference ${reference.id} is not verified for real-person generation`);
  }
}

export async function resolveImageReference(
  reference: CharacterReference,
  store: ContentFactoryStore,
  selectedCharacterId?: string,
) {
  await assertReferenceConsent(reference, store, selectedCharacterId);

  if (reference.kind !== "image") {
    throw new Error(
      `reference ${reference.id} is ${reference.kind}; the portable V2 generation path currently supports stored image references only`,
    );
  }

  if (isObjectStorageConfigured() && reference.storageKey) {
    if (await objectExists(reference.storageKey)) {
      return createReadUrl(reference.storageKey, 1800);
    }
  }

  const fallback = publicHttps(reference.sourceUrl);
  if (fallback) return fallback;

  throw new Error(
    `reference ${reference.id} has no readable object-storage asset or public HTTPS source URL`,
  );
}

export async function resolveImageReferenceIds(
  ids: string[],
  store: ContentFactoryStore,
  selectedCharacterId?: string,
) {
  const uniqueIds = [...new Set(ids.map((id) => id.trim()).filter(Boolean))];
  if (uniqueIds.length > 12) throw new Error("a generation can use at most 12 stored references");

  const urls: string[] = [];
  for (const id of uniqueIds) {
    const reference = await store.getReference(id);
    if (!reference) throw new Error(`reference not found: ${id}`);
    urls.push(await resolveImageReference(reference, store, selectedCharacterId));
  }
  return urls;
}
