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

  const selected = useMemo(() => characters.find((character) => character.id === selectedId), [characters, selectedId]);

  async function loadCharacters() {
    const response = await fetch("/api/characters", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load characters");
    setCharacters(data);
    setSelectedId((current) => current || data[0]?.id || "");
  }

  async function loadReferences(characterId: string) {
    if (!characterId) { setReferences([]); return; }
    const response = await fetch(`/api/references?characterId=${encodeURIComponent(characterId)}`, { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load references");
    setReferences(data);
  }

  useEffect(() => { loadCharacters().catch((err) => setError(err instanceof Error ? err.message : "Could not load characters")); }, []);
  useEffect(() => {
    loadReferences(selectedId).catch((err) => setError(err instanceof Error ? err.message : "Could not load references"));
    setReferenceAuthorized(false);
  }, [selectedId]);

  async function createCharacter(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const slug = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      const response = await fetch("/api/characters", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, slug, kind, consentStatus: kind === "real_person" ? (consentConfirmed ? "verified" : "pending") : "not_required", consentNotes: kind === "real_person" ? consentNotes : undefined }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not create character");
      setName(""); setConsentConfirmed(false); setConsentNotes("");
      await loadCharacters(); setSelectedId(data.id);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not create character"); }
    finally { setBusy(false); }
  }

  async function setConsent(status: "verified" | "revoked") {
    if (!selected) return; setBusy(true); setError("");
    try {
      const response = await fetch(`/api/characters/${encodeURIComponent(selected.id)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ consentStatus: status }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not update consent");
      await loadCharacters();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update consent"); }
    finally { setBusy(false); }
  }

  async function uploadReference(file: File) {
    if (!selected) throw new Error("Select a character first");
    if (!file.type.startsWith("image/")) throw new Error("The portable generation path currently accepts image references");
    if (selected.kind === "real_person" && (!referenceAuthorized || selected.consentStatus !== "verified")) throw new Error("Verified character consent and reference authorization are required for a real-person reference");

    const signResponse = await fetch("/api/uploads", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ filename: file.name, contentType: file.type, namespace: "references" }) });
    const signed = await signResponse.json();
    if (!signResponse.ok) throw new Error(signed.error || "Could not create upload URL");
    const uploadResponse = await fetch(signed.uploadUrl, { method: "PUT", headers: signed.headers, body: file });
    if (!uploadResponse.ok) throw new Error(`Object upload failed (${uploadResponse.status})`);
    const registerResponse = await fetch("/api/references", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ characterId: selected.id, kind: "image", storageKey: signed.storageKey, label: file.name, consentVerified: selected.kind === "real_person" ? referenceAuthorized : false }) });
    const registered = await registerResponse.json();
    if (!registerResponse.ok) throw new Error(registered.error || "Could not register reference");
    await loadReferences(selected.id); setReferenceAuthorized(false);
  }

  async function onFile(file?: File) {
    if (!file) return; setBusy(true); setError("");
    try { await uploadReference(file); }
    catch (err) { setError(err instanceof Error ? err.message : "Reference upload failed"); }
    finally { setBusy(false); }
  }

  const heroReference = references.find((reference) => reference.kind === "image");

  return (
    <main className="page">
      <div className="page-kicker">Talent</div>
      <h1 className="page-title">Build your cast.</h1>
      <p className="page-subtitle">Create persistent synthetic talent, brand characters, or consented digital twins. Their identity references become reusable Elements across projects.</p>
      {error ? <div className="alert">{error}</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, .85fr) minmax(360px, 1.15fr)", gap: 22, marginTop: 28, alignItems: "start" }}>
        <section>
          <div className="panel-flat" style={{ padding: 18 }}>
            <h2 className="section-title">Cast</h2>
            <p className="section-note">Select a character to manage identity and references.</p>
            <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", marginTop: 14 }}>
              {characters.map((character) => (
                <button key={character.id} onClick={() => setSelectedId(character.id)} className="library-card" style={{ padding: 0, textAlign: "left", cursor: "pointer", borderColor: selectedId === character.id ? "#111" : undefined }}>
                  <div className="library-thumb">
                    <div style={{ width: "100%", height: "100%", display: "grid", placeItems: "center", fontSize: 28, fontWeight: 750, color: "#666660" }}>{character.name.slice(0, 2).toUpperCase()}</div>
                  </div>
                  <div className="library-body"><div className="library-title">{character.name}</div><div className="library-meta">{character.kind.replaceAll("_", " ")}</div></div>
                </button>
              ))}
            </div>
          </div>

          <details className="panel-flat" style={{ padding: 18, marginTop: 14 }}>
            <summary style={{ cursor: "pointer", fontWeight: 700, fontSize: 13 }}>+ Create new character</summary>
            <form onSubmit={createCharacter} style={{ marginTop: 16 }}>
              <label className="field-label">Name<input required className="field" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Maya" /></label>
              <label className="field-label" style={{ marginTop: 12 }}>Type<select className="field" value={kind} onChange={(e) => { setKind(e.target.value as Character["kind"]); setConsentConfirmed(false); }}><option value="synthetic">Synthetic influencer</option><option value="real_person">Real-person digital twin</option><option value="brand_mascot">Brand mascot</option></select></label>
              {kind === "real_person" ? <>
                <label style={{ display: "flex", gap: 8, marginTop: 14, fontSize: 12, lineHeight: 1.5 }}><input type="checkbox" checked={consentConfirmed} onChange={(e) => setConsentConfirmed(e.target.checked)} /> I have authorization from this person to create and use their digital likeness.</label>
                <label className="field-label" style={{ marginTop: 12 }}>Consent notes<textarea className="field" value={consentNotes} onChange={(e) => setConsentNotes(e.target.value)} rows={3} style={{ resize: "vertical" }} /></label>
              </> : null}
              <button className="button-primary" disabled={busy || !name.trim()} style={{ margin: "16px 0 0" }}>Create character</button>
            </form>
          </details>
        </section>

        <section className="panel" style={{ overflow: "hidden" }}>
          {!selected ? <div style={{ padding: 24, color: "#777770" }}>Create or select a character.</div> : <>
            <div style={{ minHeight: 250, background: "#e9e9e5", display: "grid", placeItems: "center", overflow: "hidden" }}>
              {heroReference ? <img src={`/api/references/${encodeURIComponent(heroReference.id)}/content`} alt={selected.name} style={{ width: "100%", height: 320, objectFit: "cover" }} /> : <div style={{ fontSize: 52, fontWeight: 750, color: "#777770" }}>{selected.name.slice(0, 2).toUpperCase()}</div>}
            </div>
            <div style={{ padding: 22 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "start" }}>
                <div><h2 style={{ margin: 0, fontSize: 22, letterSpacing: "-.03em" }}>{selected.name}</h2><div className="meta" style={{ marginTop: 5 }}>{selected.kind.replaceAll("_", " ")}{selected.kind === "real_person" ? ` · consent ${selected.consentStatus}` : ""}</div></div>
                {selected.kind === "real_person" ? <div style={{ display: "flex", gap: 7 }}>{selected.consentStatus !== "verified" ? <button className="button-secondary" disabled={busy} onClick={() => setConsent("verified")}>Verify consent</button> : null}{selected.consentStatus !== "revoked" ? <button className="button-secondary" disabled={busy} onClick={() => setConsent("revoked")}>Revoke</button> : null}</div> : null}
              </div>

              <div style={{ borderTop: "1px solid var(--line)", marginTop: 20, paddingTop: 18 }}>
                <h3 className="section-title">Identity references</h3>
                <p className="section-note">Add face angles, wardrobe, lighting and recurring looks. These become reusable Elements.</p>
                {selected.kind === "real_person" ? <label style={{ display: "flex", gap: 8, fontSize: 12, lineHeight: 1.45, margin: "14px 0 10px" }}><input type="checkbox" checked={referenceAuthorized} onChange={(e) => setReferenceAuthorized(e.target.checked)} /> I confirm this uploaded reference is authorized for use with this person.</label> : null}
                <label className="reference-add" style={{ width: 120, height: 80, marginTop: 14, cursor: "pointer" }}>+ Upload<input type="file" accept="image/*" disabled={busy} hidden onChange={(e) => { void onFile(e.target.files?.[0]); e.currentTarget.value = ""; }} /></label>
                <div className="reference-row">
                  {references.filter((reference) => reference.kind === "image").map((reference) => <div className="reference-card" key={reference.id} style={{ cursor: "default" }}><img src={`/api/references/${encodeURIComponent(reference.id)}/content`} alt="" /><span>{reference.label || "Reference"}</span></div>)}
                </div>
              </div>
            </div>
          </>}
        </section>
      </div>
    </main>
  );
}
