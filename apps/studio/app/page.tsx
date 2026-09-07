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

type WorkflowId =
  | "ugc_ad"
  | "talking_creator"
  | "product_to_video"
  | "cinematic_video"
  | "reference_video"
  | "product_still"
  | "edit";

type Workflow = {
  id: WorkflowId;
  label: string;
  description: string;
  output: "Video" | "Image" | "Edit";
  wired: boolean;
};

const workflows: Workflow[] = [
  { id: "ugc_ad", label: "UGC Ad", description: "Hook, demo, and CTA with reusable cast and product context.", output: "Video", wired: true },
  { id: "talking_creator", label: "Talking Creator", description: "Creator-led delivery with performance and voice direction.", output: "Video", wired: true },
  { id: "product_to_video", label: "Product → Video", description: "Animate an approved product frame into a polished commercial shot.", output: "Video", wired: true },
  { id: "cinematic_video", label: "Cinematic", description: "Multi-shot direction with camera, lighting, timing, and continuity.", output: "Video", wired: true },
  { id: "reference_video", label: "Reference Video", description: "Preserve a visual language, subject, or performance reference.", output: "Video", wired: true },
  { id: "product_still", label: "Product Still", description: "Studio, lifestyle, or campaign-ready product imagery.", output: "Image", wired: false },
  { id: "edit", label: "Edit", description: "Preserve the source and change only what you ask for.", output: "Edit", wired: false },
];

const directionOptions = {
  setup: ["Auto", "Commercial", "Documentary", "Editorial", "Cinematic", "UGC"],
  camera: ["Auto", "Handheld", "Locked off", "Slow push", "Tracking", "POV"],
  color: ["Auto", "Natural", "Clean neutral", "High contrast", "Warm film", "Cool editorial"],
  lighting: ["Auto", "Soft daylight", "Window light", "Studio softbox", "Golden hour", "Low key"],
  performance: ["Auto", "Natural", "Confident", "Conversational", "Energetic", "Understated"],
};

function planForWorkflow(workflow: WorkflowId) {
  switch (workflow) {
    case "ugc_ad":
      return [
        { label: "Hook", detail: "Stop the scroll in the first beat." },
        { label: "Demo", detail: "Show the product or value in use." },
        { label: "CTA", detail: "Land one clear next action." },
      ];
    case "talking_creator":
      return [
        { label: "Open", detail: "Direct-to-camera hook and eye line." },
        { label: "Message", detail: "Natural creator delivery and gestures." },
        { label: "Close", detail: "Short final line with a clean hold." },
      ];
    case "product_to_video":
      return [
        { label: "Hero frame", detail: "Lock product identity and starting composition." },
        { label: "Motion", detail: "Add one controlled camera or product move." },
      ];
    case "cinematic_video":
      return [
        { label: "Establish", detail: "Set space, subject, and visual language." },
        { label: "Detail", detail: "Move closer without breaking continuity." },
        { label: "Hero", detail: "Finish on the strongest visual beat." },
      ];
    case "reference_video":
      return [
        { label: "Source lock", detail: "Identify what the reference must preserve." },
        { label: "Variation", detail: "Change only the requested creative dimension." },
      ];
    case "product_still":
      return [
        { label: "Composition", detail: "Product, surface, background, and framing." },
        { label: "Look", detail: "Lighting, palette, material detail, and campaign intent." },
      ];
    case "edit":
      return [
        { label: "Preserve", detail: "Lock source identity, layout, and unaffected regions." },
        { label: "Change", detail: "Apply only the requested edit." },
      ];
  }
}

export default function HomePage() {
  const [workflowId, setWorkflowId] = useState<WorkflowId>("ugc_ad");
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

  const workflow = workflows.find((item) => item.id === workflowId) ?? workflows[0];
  const plan = useMemo(() => planForWorkflow(workflowId), [workflowId]);
  const selectedCharacter = useMemo(
    () => characters.find((character) => character.id === characterId),
    [characters, characterId],
  );
  const selectedProject = useMemo(
    () => projects.find((project) => project.id === projectId),
    [projects, projectId],
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
      `workflow: ${workflow.label}`,
      setup !== "Auto" ? `format/style: ${setup}` : "",
      camera !== "Auto" ? `camera: ${camera}` : "",
      color !== "Auto" ? `color: ${color}` : "",
      lighting !== "Auto" ? `lighting: ${lighting}` : "",
      performance !== "Auto" ? `performance: ${performance}` : "",
    ].filter(Boolean);
    return `${prompt.trim()}\n\nCreative direction: ${direction.join("; ")}.`;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!workflow.wired) return;
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

  const control = (
    label: string,
    value: string,
    values: readonly string[],
    setValue: (value: string) => void,
  ) => (
    <label className="control-chip">
      <span>{label}</span>
      <select value={value} onChange={(event) => setValue(event.target.value)}>
        {values.map((option) => <option key={option}>{option}</option>)}
      </select>
    </label>
  );

  return (
    <main className="page studio-page">
      <div className="page-kicker">Create</div>
      <div className="studio-heading-row">
        <div>
          <h1 className="page-title">What do you want to make?</h1>
          <p className="page-subtitle">Choose a workflow, attach reusable Elements, direct the scene, then review the production plan before spending.</p>
        </div>
        <div className="preview-pill">UX preview</div>
      </div>

      <section className="workflow-strip" aria-label="Creative workflows">
        {workflows.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`workflow-card ${workflowId === item.id ? "active" : ""}`}
            onClick={() => setWorkflowId(item.id)}
          >
            <div className="workflow-card-top">
              <span>{item.label}</span>
              <span className="workflow-output">{item.output}</span>
            </div>
            <p>{item.description}</p>
            {!item.wired ? <span className="preview-only">Preview only</span> : null}
          </button>
        ))}
      </section>

      <div className="studio-grid ux-grid">
        <form onSubmit={submit} className="panel creator">
          <div className="creator-top elements-zone">
            <div className="section-heading-row">
              <div>
                <h2 className="section-title">Elements</h2>
                <p className="section-note">Reusable people, product, location, and references that should stay consistent.</p>
              </div>
              <Link href="/library" className="text-link">Open library</Link>
            </div>

            <div className="element-pills">
              <button type="button" className={`element-pill ${selectedCharacter ? "filled" : ""}`}>Cast{selectedCharacter ? ` · ${selectedCharacter.name}` : ""}</button>
              <button type="button" className="element-pill">Product</button>
              <button type="button" className="element-pill">Location</button>
              <button type="button" className={`element-pill ${referenceIds.length ? "filled" : ""}`}>References{referenceIds.length ? ` · ${referenceIds.length}` : ""}</button>
              <button type="button" className="element-pill">Style</button>
            </div>

            <div className="reference-row compact-references">
              {references.slice(0, 8).map((reference) => {
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

          <div className="creator-stage director-stage">
            <div className="director-label">Director</div>
            <textarea
              required
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              className="prompt-box"
              placeholder={workflowId === "ugc_ad" ? "Describe the ad, hook, offer, and what the creator should do…" : workflowId === "product_to_video" ? "Describe how the approved product frame should move…" : "Describe the scene you imagine…"}
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

            <div className="generation-bar ux-generation-bar">
              <div className="render-stage-toggle" aria-label="Render stage">
                <button type="button" className={tier === "draft" ? "active" : ""} onClick={() => setTier("draft")}>Draft</button>
                <button type="button" className={tier !== "draft" ? "active" : ""} onClick={() => setTier("quality")}>Final</button>
              </div>
              <select className="compact-field" value={resolution} onChange={(e) => setResolution(e.target.value)}><option>1080p</option><option>720p</option><option>480p</option></select>
              <select className="compact-field" value={aspectRatio} onChange={(e) => setAspectRatio(e.target.value)}><option>9:16</option><option>16:9</option><option>1:1</option><option>4:5</option></select>
              <select className="compact-field" value={duration} onChange={(e) => setDuration(Number(e.target.value))}><option value={5}>5s</option><option value={8}>8s</option><option value={10}>10s</option><option value={15}>15s</option><option value={30}>30s</option></select>
              <label className="compact-field audio-toggle"><input type="checkbox" checked={generateAudio} onChange={(e) => setGenerateAudio(e.target.checked)} /> Audio</label>
              <button className="button-primary" disabled={busy || !prompt.trim() || !workflow.wired}>{busy ? "Working…" : workflow.wired ? "Generate" : "Preview only"}</button>
            </div>
          </div>
        </form>

        <aside className="side-stack ux-side-stack">
          <section className="panel-flat side-panel plan-panel">
            <div className="section-heading-row">
              <div>
                <div className="plan-kicker">Production plan</div>
                <h2 className="section-title">{workflow.label}</h2>
              </div>
              <span className="plan-status">Draft</span>
            </div>

            <div className="plan-summary-grid">
              <div><span>Output</span><strong>{workflow.output}</strong></div>
              <div><span>Format</span><strong>{aspectRatio}</strong></div>
              <div><span>Length</span><strong>{workflow.output === "Image" ? "Still" : `${duration}s`}</strong></div>
              <div><span>Cast</span><strong>{selectedCharacter?.name || "None"}</strong></div>
            </div>

            <div className="plan-shot-list">
              {plan.map((shot, index) => (
                <div className="plan-shot" key={shot.label}>
                  <span className="shot-index">{String(index + 1).padStart(2, "0")}</span>
                  <div><strong>{shot.label}</strong><p>{shot.detail}</p></div>
                </div>
              ))}
            </div>

            <div className="plan-locks">
              <div className="plan-lock-label">Continuity locks</div>
              <div className="plan-lock-row">
                {selectedCharacter ? <span>Identity</span> : null}
                {referenceIds.length ? <span>{referenceIds.length} references</span> : null}
                {lighting !== "Auto" ? <span>{lighting}</span> : null}
                {camera !== "Auto" ? <span>{camera}</span> : null}
                {!selectedCharacter && !referenceIds.length && lighting === "Auto" && camera === "Auto" ? <span className="empty-lock">No locks yet</span> : null}
              </div>
            </div>

            <div className="plan-footnote">This is the visible interpretation layer. The orchestration service will eventually compile this plan into model-specific instructions before generation.</div>
          </section>

          <section className="panel-flat side-panel">
            <h2 className="section-title">Production context</h2>
            <p className="section-note">Attach the take to a project and reusable cast.</p>
            <label className="field-label field-spacing">Project<select className="field" value={projectId} onChange={(e) => setProjectId(e.target.value)}><option value="">No project</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
            <label className="field-label field-spacing">Cast<select className="field" value={characterId} onChange={(e) => setCharacterId(e.target.value)}><option value="">No character</option>{characters.map((character) => <option key={character.id} value={character.id}>{character.name}</option>)}</select></label>
            {selectedCharacter ? (
              <div className="cast-card">
                <div className="avatar">{selectedCharacter.name.slice(0, 2).toUpperCase()}</div>
                <div className="truncate-box">
                  <div className="cast-name">{selectedCharacter.name}</div>
                  <div className="meta">{selectedCharacter.kind.replaceAll("_", " ")}{selectedCharacter.kind === "real_person" ? ` · ${selectedCharacter.consentStatus}` : ""}</div>
                </div>
              </div>
            ) : null}
            {selectedProject ? <div className="meta context-meta">Working in {selectedProject.name}</div> : null}
          </section>

          <section className="panel-flat side-panel">
            <div className="section-heading-row current-take-head">
              <div><h2 className="section-title">Current take</h2><p className="section-note">Execution details stay downstream of the creative plan.</p></div>
              {job && pollUrl ? <button type="button" className="button-secondary" onClick={refresh} disabled={busy}>Refresh</button> : null}
            </div>
            {!job ? <p className="section-note current-take-empty">No generation submitted yet.</p> : (
              <div className="take-details">
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
