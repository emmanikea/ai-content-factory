"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type Character = {
  id: string;
  name: string;
  slug: string;
  kind: "real_person" | "synthetic" | "brand_mascot";
  consentStatus: "not_required" | "pending" | "verified" | "revoked";
  consentNotes?: string;
};

type Reference = {
  id: string;
  characterId?: string;
  kind: string;
  storageKey: string;
  label?: string;
  consentVerified: boolean;
};

const input: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  border: "1px solid #d7d7d2",
  borderRadius: 8,
  padding: "10px 12px",
  background: "white",
  fontSize: 14,
};

export default function CharactersPage() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [references, setReferences] = useState<Reference[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [name, setName] = useState("");
  const [kind, setKind] = useState<Character["kind"]>("synthetic");
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [consentNotes, setConsentNotes] = useState("");
  const [referenceAuthorized, setReferenceAuthorized] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const selected = useMemo(
    () => characters.find((character) => character.id === selectedId),
    [characters, selectedId],
  );

  async function loadCharacters() {
    const response = await fetch("/api/characters", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load characters");
    setCharacters(data);
    setSelectedId((current) => current || data[0]?.id || "");
  }

  async function loadReferences(characterId: string) {
    if (!characterId) {
      setReferences([]);
      return;
    }
    const response = await fetch(`/api/references?characterId=${encodeURIComponent(characterId)}`, { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load references");
    setReferences(data);
  }

  useEffect(() => {
    loadCharacters().catch((err) => setError(err instanceof Error ? err.message : "Could not load characters"));
  }, []);

  useEffect(() => {
    loadReferences(selectedId).catch((err) => setError(err instanceof Error ? err.message : "Could not load references"));
    setReferenceAuthorized(false);
  }, [selectedId]);

  async function createCharacter(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const slug = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      const response = await fetch("/api/characters", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          slug,
          kind,
          consentStatus: kind === "real_person" ? (consentConfirmed ? "verified" : "pending") : "not_required",
          consentNotes: kind === "real_person" ? consentNotes : undefined,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not create character");
      setName("");
      setConsentConfirmed(false);
      setConsentNotes("");
      await loadCharacters();
      setSelectedId(data.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create character");
    } finally {
      setBusy(false);
    }
  }

  async function setConsent(status: "verified" | "revoked") {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`/api/characters/${encodeURIComponent(selected.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consentStatus: status }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not update consent");
      await loadCharacters();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update consent");
    } finally {
      setBusy(false);
    }
  }

  async function uploadReference(file: File) {
    if (!selected) throw new Error("Select a character first");
    if (!file.type.startsWith("image/")) throw new Error("The portable generation path currently accepts image references");
    if (selected.kind === "real_person" && (!referenceAuthorized || selected.consentStatus !== "verified")) {
      throw new Error("Verified character consent and reference authorization are required for a real-person reference");
    }

    const signResponse = await fetch("/api/uploads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, contentType: file.type, namespace: "references" }),
    });
    const signed = await signResponse.json();
    if (!signResponse.ok) throw new Error(signed.error || "Could not create upload URL");

    const uploadResponse = await fetch(signed.uploadUrl, {
      method: "PUT",
      headers: signed.headers,
      body: file,
    });
    if (!uploadResponse.ok) throw new Error(`Object upload failed (${uploadResponse.status})`);

    const registerResponse = await fetch("/api/references", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        characterId: selected.id,
        kind: "image",
        storageKey: signed.storageKey,
        label: file.name,
        consentVerified: selected.kind === "real_person" ? referenceAuthorized : false,
      }),
    });
    const registered = await registerResponse.json();
    if (!registerResponse.ok) throw new Error(registered.error || "Could not register reference");
    await loadReferences(selected.id);
    setReferenceAuthorized(false);
  }

  async function onFile(file?: File) {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      await uploadReference(file);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reference upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 1120, margin: "0 auto", padding: "38px 24px 80px" }}>
      <h1 style={{ fontSize: 30, margin: "0 0 8px" }}>Characters</h1>
      <p style={{ color: "#666", marginTop: 0 }}>Manage synthetic talent, brand characters and consented real-person digital twins.</p>

      {error ? <div style={{ margin: "18px 0", padding: 12, border: "1px solid #d9b8b8", borderRadius: 8, background: "#fff7f7" }}>{error}</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(300px, .85fr) minmax(0, 1.15fr)", gap: 24, alignItems: "start" }}>
        <section style={{ background: "white", border: "1px solid #e2e2dd", borderRadius: 14, padding: 22 }}>
          <h2 style={{ fontSize: 17, marginTop: 0 }}>Add character</h2>
          <form onSubmit={createCharacter}>
            <label style={{ display: "block", fontSize: 13 }}>Name<input required value={name} onChange={(e) => setName(e.target.value)} style={{ ...input, marginTop: 6 }} /></label>
            <label style={{ display: "block", fontSize: 13, marginTop: 14 }}>Type<select value={kind} onChange={(e) => { setKind(e.target.value as Character["kind"]); setConsentConfirmed(false); }} style={{ ...input, marginTop: 6 }}><option value="synthetic">Synthetic influencer</option><option value="real_person">Real-person digital twin</option><option value="brand_mascot">Brand mascot</option></select></label>
            {kind === "real_person" ? <>
              <label style={{ display: "flex", gap: 8, marginTop: 14, fontSize: 13, lineHeight: 1.4 }}><input type="checkbox" checked={consentConfirmed} onChange={(e) => setConsentConfirmed(e.target.checked)} /> I have authorization from this person to create and use their digital likeness.</label>
              <label style={{ display: "block", fontSize: 13, marginTop: 14 }}>Consent notes<textarea value={consentNotes} onChange={(e) => setConsentNotes(e.target.value)} rows={3} style={{ ...input, marginTop: 6, resize: "vertical" }} /></label>
            </> : null}
            <button disabled={busy || !name.trim()} style={{ marginTop: 16, border: 0, borderRadius: 8, padding: "10px 14px", background: "#111", color: "white", fontWeight: 700 }}>Create</button>
          </form>
        </section>

        <section style={{ background: "white", border: "1px solid #e2e2dd", borderRadius: 14, padding: 22 }}>
          <h2 style={{ fontSize: 17, marginTop: 0 }}>Talent library</h2>
          {characters.length === 0 ? <p style={{ color: "#777" }}>No characters yet.</p> : <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)} style={input}>{characters.map((character) => <option key={character.id} value={character.id}>{character.name} · {character.kind.replaceAll("_", " ")}</option>)}</select>}

          {selected ? <div style={{ marginTop: 18 }}>
            <div style={{ fontSize: 14 }}><strong>{selected.name}</strong></div>
            <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>Consent: {selected.consentStatus}</div>
            {selected.kind === "real_person" ? <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              {selected.consentStatus !== "verified" ? <button disabled={busy} onClick={() => setConsent("verified")} style={{ padding: "8px 10px" }}>Mark verified</button> : null}
              {selected.consentStatus !== "revoked" ? <button disabled={busy} onClick={() => setConsent("revoked")} style={{ padding: "8px 10px" }}>Revoke</button> : null}
            </div> : null}

            <div style={{ borderTop: "1px solid #ecece7", marginTop: 22, paddingTop: 18 }}>
              <h3 style={{ fontSize: 15, margin: "0 0 10px" }}>Identity references</h3>
              {selected.kind === "real_person" ? <label style={{ display: "flex", gap: 8, fontSize: 13, lineHeight: 1.4, marginBottom: 10 }}><input type="checkbox" checked={referenceAuthorized} onChange={(e) => setReferenceAuthorized(e.target.checked)} /> I confirm this uploaded reference is authorized for use with this person.</label> : null}
              <input type="file" accept="image/*" disabled={busy} onChange={(e) => { void onFile(e.target.files?.[0]); e.currentTarget.value = ""; }} />
              <div style={{ marginTop: 14, display: "grid", gap: 8 }}>
                {references.length === 0 ? <span style={{ color: "#777", fontSize: 13 }}>No stored references.</span> : references.map((reference) => <div key={reference.id} style={{ border: "1px solid #ecece7", borderRadius: 8, padding: 10, fontSize: 13 }}><strong>{reference.label || "Image reference"}</strong><div style={{ color: "#777", marginTop: 3, wordBreak: "break-all" }}>{reference.id}</div></div>)}
              </div>
            </div>
          </div> : null}
        </section>
      </div>
    </main>
  );
}
