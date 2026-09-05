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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load jobs");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <main style={{ maxWidth: 1120, margin: "0 auto", padding: "38px 24px 80px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
        <div><h1 style={{ fontSize: 30, margin: "0 0 8px" }}>Jobs</h1><p style={{ color: "#666", marginTop: 0 }}>Factory-level history across OpenRouter and ComfyUI.</p></div>
        <button onClick={() => void load()} disabled={busy} style={{ padding: "8px 11px" }}>Refresh</button>
      </div>
      {error ? <div style={{ margin: "18px 0", padding: 12, border: "1px solid #d9b8b8", borderRadius: 8, background: "#fff7f7" }}>{error}</div> : null}

      <section style={{ background: "white", border: "1px solid #e2e2dd", borderRadius: 14, overflow: "hidden" }}>
        {jobs.length === 0 ? <p style={{ padding: 22, color: "#777" }}>No generations yet.</p> : jobs.map((job, index) => (
          <div key={job.id} style={{ padding: 16, borderTop: index ? "1px solid #ecece7" : 0, display: "grid", gridTemplateColumns: "110px minmax(0,1fr) 160px", gap: 16, alignItems: "start" }}>
            <div><strong style={{ fontSize: 13 }}>{job.status}</strong><div style={{ color: "#777", fontSize: 12, marginTop: 4 }}>{job.provider}</div></div>
            <div><div style={{ fontSize: 13, lineHeight: 1.45 }}>{job.prompt}</div><div style={{ color: "#888", fontSize: 11, marginTop: 5 }}>{job.model || "provider default"} · {job.tier}</div><div style={{ color: "#aaa", fontSize: 10, marginTop: 4, wordBreak: "break-all" }}>{job.id}</div></div>
            <div style={{ textAlign: "right", fontSize: 12 }}>
              <div>{job.actualCostUsd != null ? `$${job.actualCostUsd.toFixed(4)} actual` : job.estimatedCostUsd != null ? `$${job.estimatedCostUsd.toFixed(4)} est.` : "cost pending"}</div>
              <div style={{ color: "#888", marginTop: 4 }}>{new Date(job.createdAt).toLocaleString()}</div>
              {job.status === "completed" ? <a href={`/api/generations/${job.id}/content?index=0`} target="_blank" rel="noreferrer" style={{ display: "inline-block", marginTop: 7, color: "#111" }}>Open output</a> : null}
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}
