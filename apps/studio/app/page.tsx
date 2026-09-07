"use client";

import Link from "next/link";
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

const directionOptions = {
  setup: ["Auto", "Commercial", "Documentary", "Editorial", "Cinematic", "UGC"],
  camera: ["Auto", "Handheld", "Locked off", "Slow push", "Tracking", "POV"],
  color: ["Auto", "Natural", "Clean neutral", "High contrast", "Warm film", "Cool editorial"],
  lighting: ["Auto", "Soft daylight", "Window light", "Studio softbox", "Golden hour", "Low key"],
  performance: ["Auto", "Natural", "Confident", "Conversational", "Energetic", "Understated"],
};

export default function HomePage() {
  const [prompt, setPrompt] = useState("");
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [tier, setTier] = useState("quality");
  const [duration, setDuration] = useState(8);
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [resolution, setResolution] = useState("1080p");
  const [generateAudio, setGenerateAudio] = useState(true);
  const [projectId, setProjectId] = useState("");
  const [characterId, setCharacterId] = useState("");
  const [referenceIds, setReferenceIds] = useState<string[]>([]);
  const [referenceUrl, setReferenceUrl] = useState("");
  const [setup, setSetup] = useState("Auto");
  const [camera, setCamera] = useState("Auto");
  const [color, setColor] = useState("Auto");
  const [lighting, setLighting] = useState("Auto");
  const [performance, setPerformance] = useState("Auto");
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
  const selectedProject = useMemo(() => projects.find((project) => project.id === projectId), [projects, projectId]);

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
    ])
      .then(([characterData, projectData]) => {
        setCharacters(characterData);
        setProjects(projectData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load Studio data"));
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

  function directedPrompt() {
    const direction = [
      setup !== "Auto" ? `format/style: ${setup}` : "",
      camera !== "Auto" ? `camera: ${camera}` : "",
      color !== "Auto" ? `color: ${color}` : "",
      lighting !== "Auto" ? `lighting: ${lighting}` : "",
      performance !== "Auto" ? `performance: ${performance}` : "",
    ].filter(Boolean);
    return direction.length ? `${prompt.trim()}\n\nCreative direction: ${direction.join("; ")}.` : prompt.trim();
  }

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
          prompt: directedPrompt(),
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

  const control = (label: string, value: string, values: readonly string[], setValue: (value: string) => void) => (
    <label className="control-chip">
      <span>{label}</span>
      <select value={value} onChange={(event) => setValue(event.target.value)}>
        {values.map((option) => <option key={option}>{option}</option>)}
      </select>
    </label>
  );

  return (
    <main className="page">
      <div className="page-kicker">Create</div>
      <h1 className="page-title">Bring the scene to life.</h1>
      <p className="page-subtitle">Choose your cast and references, direct the shot, and let the factory route the generation to the right engine.</p>

      <div className="studio-grid">
        <form onSubmit={submit} className="panel creator">
          <div className="creator-top">
            <div className="section-title">References <span style={{ color: "#8b8b85", fontWeight: 500 }}>{referenceIds.length}/{references.length}</span></div>
            <div className="reference-row">
              {references.slice(0, 10).map((reference) => {
                const selected = referenceIds.includes(reference.id);
                return (
                  <button
                    type="button"
                    key={reference.id}
                    className={`reference-card ${selected ? "selected" : ""}`}
                    onClick={() => setReferenceIds((current) => selected ? current.filter((id) => id !== reference.id) : [...current, reference.id])}
                    title={reference.label || reference.id}
                  >
                    <img src={`/api/references/${encodeURIComponent(reference.id)}/content`} alt="" />
                    <span>{reference.label || "Reference"}</span>
                  </button>
                );
              })}
              <Link href="/characters" className="reference-add">+ Add<br />reference</Link>
            </div>
          </div>

          <div className="creator-stage">
            <textarea
              required
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              className="prompt-box"
              placeholder="Describe the scene you imagine…"
            />
          </div>

          <div className="creator-controls">
            <div className="control-strip">
              {control("Setup", setup, directionOptions.setup, setSetup)}
              {control("Camera", camera, directionOptions.camera, setCamera)}
              {control("Color", color, directionOptions.color, setColor)}
              {control("Lighting", lighting, directionOptions.lighting, setLighting)}
              {control("Performance", performance, directionOptions.performance, setPerformance)}
            </div>

            <details className="advanced">
              <summary>Advanced routing & external reference</summary>
              <div className="advanced-grid">
                <label className="field-label">Quality tier<select className="field" value={tier} onChange={(e) => setTier(e.target.value)}><option value="draft">Draft</option><option value="standard">Standard</option><option value="quality">Quality</option><option value="max">Max</option></select></label>
                <label className="field-label">Provider<select className="field" value={provider} onChange={(e) => setProvider(e.target.value)}><option value="">Auto</option><option value="openrouter">OpenRouter</option><option value="comfyui">ComfyUI</option></select></label>
                <label className="field-label">Model<input className="field" value={model} onChange={(e) => setModel(e.target.value)} placeholder="Auto" /></label>
                <label className="field-label">External HTTPS image<input className="field" value={referenceUrl} onChange={(e) => setReferenceUrl(e.target.value)} placeholder="https://…" disabled={selectedCharacter?.kind === "real_person"} /></label>
              </div>
            </details>

            {error ? <div className="alert">{error}</div> : null}

            <div className="generation-bar">
              <select className="compact-field" value={resolution} onChange={(e) => setResolution(e.target.value)}><option>1080p</option><option>720p</option><option>480p</option></select>
              <select className="compact-field" value={aspectRatio} onChange={(e) => setAspectRatio(e.target.value)}><option>9:16</option><option>16:9</option><option>1:1</option><option>4:5</option></select>
              <select className="compact-field" value={duration} onChange={(e) => setDuration(Number(e.target.value))}><option value={5}>5s</option><option value={8}>8s</option><option value={10}>10s</option><option value={15}>15s</option><option value={30}>30s</option></select>
              <label className="compact-field" style={{ display: "flex", alignItems: "center", gap: 7 }}><input type="checkbox" checked={generateAudio} onChange={(e) => setGenerateAudio(e.target.checked)} /> Audio</label>
              <button className="button-primary" disabled={busy || !prompt.trim()}>{busy ? "Working…" : "Generate"}</button>
            </div>
          </div>
        </form>

        <aside className="side-stack">
          <section className="panel-flat side-panel">
            <h2 className="section-title">Production</h2>
            <p className="section-note">Keep the scene attached to a project and reusable cast.</p>
            <label className="field-label" style={{ marginTop: 14 }}>Project<select className="field" value={projectId} onChange={(e) => setProjectId(e.target.value)}><option value="">No project</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
            <label className="field-label" style={{ marginTop: 12 }}>Cast<select className="field" value={characterId} onChange={(e) => setCharacterId(e.target.value)}><option value="">No character</option>{characters.map((character) => <option key={character.id} value={character.id}>{character.name}</option>)}</select></label>
            {selectedCharacter ? (
              <div className="cast-card">
                <div className="avatar">{selectedCharacter.name.slice(0, 2).toUpperCase()}</div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{selectedCharacter.name}</div>
                  <div className="meta">{selectedCharacter.kind.replaceAll("_", " ")}{selectedCharacter.kind === "real_person" ? ` · ${selectedCharacter.consentStatus}` : ""}</div>
                </div>
              </div>
            ) : null}
            {selectedProject ? <div className="meta" style={{ marginTop: 10 }}>Working in {selectedProject.name}</div> : null}
          </section>

          <section className="panel-flat side-panel">
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
              <div><h2 className="section-title">Current take</h2><p className="section-note">Provider details stay here, not in the creative surface.</p></div>
              {job && pollUrl ? <button type="button" className="button-secondary" onClick={refresh} disabled={busy}>Refresh</button> : null}
            </div>
            {!job ? <p className="section-note" style={{ marginTop: 14 }}>No generation submitted yet.</p> : (
              <div style={{ marginTop: 14, fontSize: 12, lineHeight: 1.65 }}>
                <div><span className="status-dot" />{job.status}</div>
                <div className="meta">{job.model || "Auto model"} · {job.provider}</div>
                {typeof job.estimatedCostUsd === "number" ? <div className="meta">Estimated ${job.estimatedCostUsd.toFixed(4)}</div> : null}
                {job.reused ? <div className="meta">Reused existing job</div> : null}
                {job.error ? <div className="alert">{job.error}</div> : null}
                {job.playbackUrl ? <video className="job-video" src={job.playbackUrl} controls preload="metadata" /> : null}
              </div>
            )}
          </section>
        </aside>
      </div>
    </main>
  );
}
