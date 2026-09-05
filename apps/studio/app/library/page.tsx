"use client";

import { useEffect, useMemo, useState } from "react";

type Character = { id: string; name: string; kind: string };
type Reference = {
  id: string;
  characterId?: string;
  kind: "image" | "video" | "audio" | "performance" | "location" | "wardrobe";
  label?: string;
  consentVerified: boolean;
};

const filters = ["all", "image", "video", "audio", "performance", "location", "wardrobe"] as const;

export default function LibraryPage() {
  const [references, setReferences] = useState<Reference[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [filter, setFilter] = useState<(typeof filters)[number]>("all");
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      fetch("/api/references", { cache: "no-store" }).then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not load references");
        return data as Reference[];
      }),
      fetch("/api/characters", { cache: "no-store" }).then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not load characters");
        return data as Character[];
      }),
    ])
      .then(([referenceData, characterData]) => {
        setReferences(referenceData);
        setCharacters(characterData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load library"));
  }, []);

  const names = useMemo(() => new Map(characters.map((character) => [character.id, character.name])), [characters]);
  const visible = filter === "all" ? references : references.filter((reference) => reference.kind === filter);

  return (
    <main className="page">
      <div className="page-kicker">Elements</div>
      <h1 className="page-title">Library</h1>
      <p className="page-subtitle">
        Reusable people, references, performances, locations and production assets. Create once, reuse across projects and generations.
      </p>

      <div className="toolbar">
        {filters.map((item) => (
          <button key={item} className={`pill ${filter === item ? "active" : ""}`} onClick={() => setFilter(item)}>
            {item === "all" ? "All" : item[0].toUpperCase() + item.slice(1)}
          </button>
        ))}
      </div>

      {error ? <div className="alert">{error}</div> : null}

      <div className="card-grid">
        {visible.map((reference) => (
          <article className="library-card" key={reference.id}>
            <div className="library-thumb">
              {reference.kind === "image" ? (
                <img src={`/api/references/${encodeURIComponent(reference.id)}/content`} alt={reference.label || "Reference"} loading="lazy" />
              ) : (
                <div style={{ height: "100%", display: "grid", placeItems: "center", color: "#777770", fontSize: 12 }}>
                  {reference.kind.toUpperCase()}
                </div>
              )}
            </div>
            <div className="library-body">
              <div className="library-title">{reference.label || `${reference.kind} reference`}</div>
              <div className="library-meta">
                {reference.characterId ? names.get(reference.characterId) || "Character asset" : "Shared asset"}
                {reference.consentVerified ? " · verified" : ""}
              </div>
            </div>
          </article>
        ))}
        {visible.length === 0 ? (
          <div className="panel-flat" style={{ padding: 18, color: "#777770", fontSize: 13 }}>No matching elements yet.</div>
        ) : null}
      </div>
    </main>
  );
}
