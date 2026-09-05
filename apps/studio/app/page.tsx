"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type Job = {
  id: string;
  factoryJobId?: string;
  provider: "openrouter" | "comfyui";
  providerJobId: string;
  status: string;
  model?: string;
  playbackUrl?: string;
  error?: string;
  providerError?: string;
  estimatedCostUsd?: number;
  costBasis?: string;
  reused?: boolean;
};

type Character = {
  id: string;
  name: string;
  kind: "real_person" | "synthetic" | "brand_mascot";
  consentStatus: "not_required" | "pending" | "verified" | "revoked";
};

type Project = { id: string; name: string; projectType: string };
type Reference = { id: string; label?: string; kind: string; consentVerified: boolean };

const field: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  border: "1px solid #d7d7d2",
  borderRadius: 8,
  padding: "10px 12px",
  background: "white",
  fontSize: 14,
};

export default function HomePage() {
  const [prompt, setPrompt] = useState("");
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [tier, setTier] = useState("standard");
  const [duration, setDuration] = useState(8);
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [resolution, setResolution] = useState("720p");
  const [generateAudio, setGenerateAudio] = useState(true);
  const [projectId, setProjectId] = useState("");
  const [characterId, setCharacterId] = useState("");
  const [referenceIds, setReferenceIds] = useState<string[]>([]);
  const [referenceUrl, setReferenceUrl] = useState("");
  const [characters, setCharacters] = useState<Character[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [references, setReferences] = useState<Reference[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const selectedCharacter = useMemo(
    () => characters.find((character) => character.id === characterId),
    [characters, characterId],
  );

  const pollUrl = useMemo(() => {
    if (!job) return null;
    if (job.factoryJobId) return `/api/generations/${encodeURIComponent(job.factoryJobId)}`;
    if (job.providerJobId) return `/api/jobs/${job.provider}/${encodeURIComponent(job.providerJobId)}`;
    return null;
  }, [job]);

  useEffect(() => {
    Promise.all([
      fetch("/api/characters", { cache: "no-store" }).then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not load characters");
        return data as Character[];
      }),
      fetch("/api/projects", { cache: "no-store" }).then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not load projects");
        return data as Project[];
      }),
    ]).then(([characterData, projectData]) => {
      setCharacters(characterData);
      setProjects(projectData);
    }).catch((err) => setError(err instanceof Error ? err.message : "Could not load Studio data"));
  }, []);

  useEffect(() => {
    setReferenceIds([]);
    if (!characterId) {
      setReferences([]);
      return;
    }
    fetch(`/api/references?characterId=${encodeURIComponent(characterId)}`, { cache: "no-store" })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not load references");
        setReferences((data as Reference[]).filter((reference) => reference.kind === "image"));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load references"));
  }, [characterId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (selectedCharacter?.kind === "real_person" && selectedCharacter.consentStatus !== "verified") {
        throw new Error(`This real-person character is ${selectedCharacter.consentStatus}; verify consent in Characters before generating.`);
      }

      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          tier,
          ...(provider ? { provider } : {}),
          ...(model ? { model } : {}),
          ...(projectId ? { projectId } : {}),
          ...(characterId ? { characterId } : {}),
          ...(referenceIds.length ? { referenceIds } : {}),
          ...(referenceUrl ? { inputReferences: [{ url: referenceUrl }] } : {}),
          duration,
          resolution,
          aspectRatio,
          generateAudio,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Generation failed");
      setJob(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    if (!pollUrl) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(pollUrl, { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not fetch job");
      setJob((previous) => ({
        ...previous,
        ...data,
        factoryJobId: previous?.factoryJobId ?? data.factoryJobId ?? data.id,
        error: data.providerError ?? data.error,
      } as Job));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not fetch job");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 1120, margin: "0 auto", padding: "38px 24px 80px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 32, lineHeight: 1.1, margin: "0 0 8px" }}>Generation Studio</h1>
        <p style={{ maxWidth: 760, color: "#555", margin: 0, lineHeight: 1.5 }}>
          Generate through hosted frontier models or self-hosted ComfyUI while keeping factory jobs, characters, references and costs in one system.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.2fr) minmax(320px, .8fr)", gap: 24, alignItems: "start" }}>
        <form onSubmit={submit} style={{ background: "white", border: "1px solid #e2e2dd", borderRadius: 14, padding: 24 }}>
          <label style={{ display: "block", fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Prompt</label>
          <textarea required value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={7} style={{ ...field, resize: "vertical", lineHeight: 1.5 }} placeholder="Describe the shot, subject, performance, camera movement, environment and desired result." />

          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 14, marginTop: 18 }}>
            <label style={{ fontSize: 13 }}>Project<select value={projectId} onChange={(e) => setProjectId(e.target.value)} style={{ ...field, marginTop: 6 }}><option value="">No project</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
            <label style={{ fontSize: 13 }}>Character<select value={characterId} onChange={(e) => setCharacterId(e.target.value)} style={{ ...field, marginTop: 6 }}><option value="">No character</option>{characters.map((character) => <option key={character.id} value={character.id}>{character.name}{character.kind === "real_person" ? ` · consent ${character.consentStatus}` : ""}</option>)}</select></label>
            <label style={{ fontSize: 13 }}>Tier<select value={tier} onChange={(e) => setTier(e.target.value)} style={{ ...field, marginTop: 6 }}><option value="draft">Draft</option><option value="standard">Standard</option><option value="quality">Quality</option><option value="max">Max</option></select></label>
            <label style={{ fontSize: 13 }}>Provider<select value={provider} onChange={(e) => setProvider(e.target.value)} style={{ ...field, marginTop: 6 }}><option value="">Auto</option><option value="openrouter">OpenRouter</option><option value="comfyui">ComfyUI</option></select></label>
            <label style={{ fontSize: 13 }}>Model<input value={model} onChange={(e) => setModel(e.target.value)} style={{ ...field, marginTop: 6 }} placeholder="optional model slug" /></label>
            <label style={{ fontSize: 13 }}>Duration<input type="number" min={1} max={30} value={duration} onChange={(e) => setDuration(Number(e.target.value))} style={{ ...field, marginTop: 6 }} /></label>
            <label style={{ fontSize: 13 }}>Aspect ratio<select value={aspectRatio} onChange={(e) => setAspectRatio(e.target.value)} style={{ ...field, marginTop: 6 }}><option>9:16</option><option>16:9</option><option>1:1</option><option>4:5</option></select></label>
            <label style={{ fontSize: 13 }}>Resolution<select value={resolution} onChange={(e) => setResolution(e.target.value)} style={{ ...field, marginTop: 6 }}><option>720p</option><option>1080p</option><option>480p</option></select></label>
          </div>

          {characterId ? <label style={{ display: "block", fontSize: 13, marginTop: 14 }}>Stored image references<select multiple value={referenceIds} onChange={(e) => setReferenceIds(Array.from(e.currentTarget.selectedOptions, (option) => option.value))} style={{ ...field, marginTop: 6, minHeight: 90 }}>{references.length ? references.map((reference) => <option key={reference.id} value={reference.id}>{reference.label || reference.id}{reference.consentVerified ? " · verified" : ""}</option>) : <option disabled>No stored image references</option>}</select><span style={{ display: "block", color: "#888", fontSize: 11, marginTop: 5 }}>Use Cmd/Ctrl to select more than one.</span></label> : null}

          <details style={{ marginTop: 16 }}><summary style={{ cursor: "pointer", fontSize: 13 }}>Advanced external reference</summary><label style={{ display: "block", fontSize: 13, marginTop: 10 }}>Public HTTPS image URL<input value={referenceUrl} onChange={(e) => setReferenceUrl(e.target.value)} style={{ ...field, marginTop: 6 }} placeholder="https://…" /></label></details>

          <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 18, fontSize: 13 }}><input type="checkbox" checked={generateAudio} onChange={(e) => setGenerateAudio(e.target.checked)} /> Generate audio when supported</label>

          {error ? <div style={{ marginTop: 18, padding: 12, border: "1px solid #d9b8b8", borderRadius: 8, background: "#fff7f7", fontSize: 13 }}>{error}</div> : null}

          <button disabled={busy || !prompt.trim()} style={{ marginTop: 20, border: 0, borderRadius: 8, padding: "11px 16px", fontWeight: 700, background: "#111", color: "white", cursor: "pointer", opacity: busy ? .55 : 1 }}>{busy ? "Working…" : "Generate"}</button>
        </form>

        <section style={{ background: "white", border: "1px solid #e2e2dd", borderRadius: 14, padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}><h2 style={{ fontSize: 18, margin: 0 }}>Current job</h2>{job && pollUrl ? <button onClick={refresh} disabled={busy} style={{ border: "1px solid #d7d7d2", background: "white", borderRadius: 7, padding: "7px 10px", cursor: "pointer" }}>Refresh</button> : null}</div>
          {!job ? <p style={{ color: "#777", fontSize: 14, lineHeight: 1.5 }}>No generation submitted yet.</p> : <div style={{ marginTop: 18, fontSize: 13, lineHeight: 1.65 }}><div><strong>Status:</strong> {job.status}</div><div><strong>Provider:</strong> {job.provider}</div><div><strong>Model:</strong> {job.model || "provider default"}</div>{job.factoryJobId ? <div style={{ wordBreak: "break-all" }}><strong>Factory job:</strong> {job.factoryJobId}</div> : null}{job.providerJobId ? <div style={{ wordBreak: "break-all" }}><strong>Provider job:</strong> {job.providerJobId}</div> : null}{job.reused ? <div><strong>Idempotency:</strong> reused existing factory job</div> : null}{typeof job.estimatedCostUsd === "number" ? <div><strong>Estimated cost:</strong> ${job.estimatedCostUsd.toFixed(4)}</div> : null}{job.costBasis ? <div style={{ color: "#777" }}>{job.costBasis}</div> : null}{job.error ? <div style={{ marginTop: 12 }}><strong>Error:</strong> {job.error}</div> : null}{job.playbackUrl ? <div style={{ marginTop: 16 }}><video src={job.playbackUrl} controls preload="metadata" style={{ width: "100%", borderRadius: 8, background: "#111" }} /></div> : null}</div>}
        </section>
      </div>
    </main>
  );
}
