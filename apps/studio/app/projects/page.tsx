"use client";

import { FormEvent, useEffect, useState } from "react";

type Project = {
  id: string;
  name: string;
  projectType: string;
  status: string;
  metadata?: { brief?: string };
  createdAt: string;
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [projectType, setProjectType] = useState("social_video");
  const [brief, setBrief] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const response = await fetch("/api/projects", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load projects");
    setProjects(data);
  }

  useEffect(() => { load().catch((err) => setError(err instanceof Error ? err.message : "Could not load projects")); }, []);

  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const response = await fetch("/api/projects", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, projectType, status: "active", metadata: brief.trim() ? { brief: brief.trim() } : {} }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not create project");
      setName(""); setBrief(""); await load();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not create project"); }
    finally { setBusy(false); }
  }

  return (
    <main className="page">
      <div className="page-kicker">Production</div>
      <h1 className="page-title">Projects</h1>
      <p className="page-subtitle">Keep creative direction, generations, assets and approvals together. The project brief is the shared context for future agents and collaborators.</p>
      {error ? <div className="alert">{error}</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(300px, .75fr) minmax(0, 1.25fr)", gap: 22, marginTop: 28, alignItems: "start" }}>
        <form onSubmit={create} className="panel-flat" style={{ padding: 20 }}>
          <h2 className="section-title">New project</h2>
          <p className="section-note">Give the factory enough context to keep future work coherent.</p>
          <label className="field-label" style={{ marginTop: 16 }}>Name<input required className="field" value={name} onChange={(e) => setName(e.target.value)} placeholder="Campaign or production name" /></label>
          <label className="field-label" style={{ marginTop: 12 }}>Workflow<select className="field" value={projectType} onChange={(e) => setProjectType(e.target.value)}><option value="social_video">Social video</option><option value="ugc_ad">UGC ad</option><option value="product_ad">Product ad</option><option value="digital_twin">Digital twin</option><option value="ai_influencer">AI influencer</option><option value="experiment">Experiment</option></select></label>
          <label className="field-label" style={{ marginTop: 12 }}>Project brief<textarea className="field" rows={6} value={brief} onChange={(e) => setBrief(e.target.value)} placeholder="Audience, tone, goal, recurring cast, visual rules, do's and don'ts…" style={{ resize: "vertical", lineHeight: 1.5 }} /></label>
          <button className="button-primary" disabled={busy || !name.trim()} style={{ margin: "16px 0 0" }}>{busy ? "Creating…" : "Create project"}</button>
        </form>

        <section className="panel-flat" style={{ padding: 20 }}>
          <h2 className="section-title">Project library</h2>
          <p className="section-note">Active production contexts available from Generate.</p>
          <div style={{ display: "grid", gap: 10, marginTop: 14 }}>
            {projects.length === 0 ? <div className="meta">No projects yet.</div> : projects.map((project) => (
              <article key={project.id} style={{ border: "1px solid var(--line)", borderRadius: 12, padding: 14, background: "var(--surface-2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 14 }}>
                  <div><strong style={{ fontSize: 14 }}>{project.name}</strong><div className="meta" style={{ marginTop: 4 }}>{project.projectType.replaceAll("_", " ")} · {project.status}</div></div>
                  <div className="meta">{new Date(project.createdAt).toLocaleDateString()}</div>
                </div>
                {project.metadata?.brief ? <p style={{ margin: "10px 0 0", fontSize: 12, lineHeight: 1.5, color: "#555550" }}>{project.metadata.brief}</p> : null}
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
