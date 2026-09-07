"use client";

import { useEffect, useState } from "react";

type Generation = {
  id: string;
  provider: string;
  providerJobId?: string;
  model?: string;
  tier: string;
  status: string;
  prompt: string;
  estimatedCostUsd?: number;
  actualCostUsd?: number;
  createdAt: string;
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<Generation[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    try {
      const response = await fetch("/api/generations", { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not load jobs");
      setJobs(data);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not load jobs"); }
    finally { setBusy(false); }
  }

  useEffect(() => { void load(); }, []);

  return (
    <main className="page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", gap: 16 }}>
        <div><div className="page-kicker">Production</div><h1 className="page-title">Jobs</h1><p className="page-subtitle">Generation history across every provider, with the factory record as the source of truth.</p></div>
        <button className="button-secondary" onClick={() => void load()} disabled={busy}>{busy ? "Refreshing…" : "Refresh"}</button>
      </div>
      {error ? <div className="alert">{error}</div> : null}

      <section className="panel-flat" style={{ overflow: "hidden", marginTop: 28 }}>
        {jobs.length === 0 ? <p style={{ padding: 22, color: "#777770", fontSize: 13 }}>No generations yet.</p> : jobs.map((job, index) => (
          <article key={job.id} style={{ padding: 17, borderTop: index ? "1px solid var(--line)" : 0, display: "grid", gridTemplateColumns: "110px minmax(0,1fr) 150px", gap: 16, alignItems: "start" }}>
            <div><strong style={{ fontSize: 12, textTransform: "capitalize" }}><span className="status-dot" />{job.status}</strong><div className="meta" style={{ marginTop: 5 }}>{job.provider}</div></div>
            <div><div style={{ fontSize: 13, lineHeight: 1.5 }}>{job.prompt}</div><div className="meta" style={{ marginTop: 6 }}>{job.model || "Auto model"} · {job.tier}</div></div>
            <div style={{ textAlign: "right", fontSize: 12 }}>
              <div>{job.actualCostUsd != null ? `$${job.actualCostUsd.toFixed(4)}` : job.estimatedCostUsd != null ? `~$${job.estimatedCostUsd.toFixed(4)}` : "—"}</div>
              <div className="meta" style={{ marginTop: 4 }}>{new Date(job.createdAt).toLocaleString()}</div>
              {job.status === "completed" ? <a href={`/api/generations/${job.id}/content?index=0`} target="_blank" rel="noreferrer" style={{ display: "inline-block", marginTop: 8, fontSize: 11 }}>Open output ↗</a> : null}
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
