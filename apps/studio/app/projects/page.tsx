"use client";

import { FormEvent, useEffect, useState } from "react";

type Project = {
  id: string;
  name: string;
  projectType: string;
  status: string;
  createdAt: string;
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

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [projectType, setProjectType] = useState("social_video");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const response = await fetch("/api/projects", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load projects");
    setProjects(data);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Could not load projects"));
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, projectType, status: "active" }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not create project");
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create project");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: "38px 24px 80px" }}>
      <h1 style={{ fontSize: 30, margin: "0 0 8px" }}>Projects</h1>
      <p style={{ color: "#666", marginTop: 0 }}>Group generations, assets, approvals and costs into a production unit.</p>
      {error ? <div style={{ margin: "18px 0", padding: 12, border: "1px solid #d9b8b8", borderRadius: 8, background: "#fff7f7" }}>{error}</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(280px, .8fr) minmax(0, 1.2fr)", gap: 24, alignItems: "start" }}>
        <form onSubmit={create} style={{ background: "white", border: "1px solid #e2e2dd", borderRadius: 14, padding: 22 }}>
          <h2 style={{ fontSize: 17, marginTop: 0 }}>New project</h2>
          <label style={{ display: "block", fontSize: 13 }}>Name<input required value={name} onChange={(e) => setName(e.target.value)} style={{ ...input, marginTop: 6 }} /></label>
          <label style={{ display: "block", fontSize: 13, marginTop: 14 }}>Type<select value={projectType} onChange={(e) => setProjectType(e.target.value)} style={{ ...input, marginTop: 6 }}><option value="social_video">Social video</option><option value="ugc_ad">UGC ad</option><option value="product_ad">Product ad</option><option value="digital_twin">Digital twin</option><option value="ai_influencer">AI influencer</option><option value="experiment">Experiment</option></select></label>
          <button disabled={busy || !name.trim()} style={{ marginTop: 16, border: 0, borderRadius: 8, padding: "10px 14px", background: "#111", color: "white", fontWeight: 700 }}>Create</button>
        </form>

        <section style={{ background: "white", border: "1px solid #e2e2dd", borderRadius: 14, padding: 22 }}>
          <h2 style={{ fontSize: 17, marginTop: 0 }}>Project library</h2>
          {projects.length === 0 ? <p style={{ color: "#777" }}>No projects yet.</p> : <div style={{ display: "grid", gap: 9 }}>{projects.map((project) => <div key={project.id} style={{ border: "1px solid #ecece7", borderRadius: 9, padding: 12 }}><strong style={{ fontSize: 14 }}>{project.name}</strong><div style={{ fontSize: 12, color: "#777", marginTop: 4 }}>{project.projectType.replaceAll("_", " ")} · {project.status}</div><div style={{ fontSize: 11, color: "#999", marginTop: 5, wordBreak: "break-all" }}>{project.id}</div></div>)}</div>}
        </section>
      </div>
    </main>
  );
}
