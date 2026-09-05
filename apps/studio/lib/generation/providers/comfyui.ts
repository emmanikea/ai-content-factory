import type {
  GenerationJob,
  GenerationRequest,
  VideoProvider,
} from "../types";

function baseUrl(): string {
  const url = process.env.COMFYUI_BASE_URL;
  if (!url) throw new Error("COMFYUI_BASE_URL is not configured");
  return url.replace(/\/$/, "");
}

function authHeaders(): HeadersInit {
  const token = process.env.COMFYUI_API_TOKEN;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function comfy(path: string, init?: RequestInit) {
  const response = await fetch(`${baseUrl()}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`ComfyUI ${response.status}: ${body.slice(0, 1200)}`);
  }
  return response.json();
}

function workflowFromRequest(input: GenerationRequest): Record<string, unknown> {
  const direct = input.providerOptions?.workflow;
  if (direct && typeof direct === "object") {
    return direct as Record<string, unknown>;
  }

  const encoded = process.env.COMFYUI_WORKFLOW_JSON;
  if (!encoded) {
    throw new Error(
      "ComfyUI needs providerOptions.workflow or COMFYUI_WORKFLOW_JSON. Export an API-format workflow from ComfyUI and provide it server-side.",
    );
  }

  const workflow = JSON.parse(encoded) as Record<string, any>;
  const bindings = input.providerOptions?.bindings as
    | Record<string, { node: string; input: string }>
    | undefined;

  // Optional lightweight binding map lets a saved graph remain provider-specific
  // without teaching the application about node IDs.
  const values: Record<string, unknown> = {
    prompt: input.prompt,
    duration: input.duration,
    resolution: input.resolution,
    aspectRatio: input.aspectRatio,
    generateAudio: input.generateAudio,
  };

  if (bindings) {
    for (const [key, binding] of Object.entries(bindings)) {
      const value = values[key];
      if (value === undefined) continue;
      const node = workflow[binding.node] as Record<string, any> | undefined;
      if (!node?.inputs) continue;
      node.inputs[binding.input] = value;
    }
  }

  return workflow;
}

function collectOutputUrls(historyEntry: Record<string, any>): string[] {
  const urls: string[] = [];
  const outputs = historyEntry.outputs ?? {};

  for (const output of Object.values(outputs) as Array<Record<string, any>>) {
    for (const key of ["videos", "gifs", "images"]) {
      const files = output?.[key];
      if (!Array.isArray(files)) continue;
      for (const file of files) {
        if (!file?.filename) continue;
        const params = new URLSearchParams({ filename: file.filename });
        if (file.subfolder) params.set("subfolder", file.subfolder);
        if (file.type) params.set("type", file.type);
        urls.push(`${baseUrl()}/view?${params.toString()}`);
      }
    }
  }

  return urls;
}

export const comfyUiProvider: VideoProvider = {
  async submit(input: GenerationRequest): Promise<GenerationJob> {
    const workflow = workflowFromRequest(input);
    const raw = await comfy("/prompt", {
      method: "POST",
      body: JSON.stringify({
        prompt: workflow,
        client_id: process.env.COMFYUI_CLIENT_ID ?? "ai-content-factory-studio",
      }),
    });

    if (!raw.prompt_id) {
      throw new Error(`ComfyUI did not return prompt_id: ${JSON.stringify(raw)}`);
    }

    return {
      id: `comfyui:${raw.prompt_id}`,
      provider: "comfyui",
      providerJobId: raw.prompt_id,
      model: input.model,
      status: "queued",
      raw,
    };
  },

  async get(providerJobId: string): Promise<GenerationJob> {
    const raw = await comfy(`/history/${encodeURIComponent(providerJobId)}`);
    const entry = raw?.[providerJobId];

    if (!entry) {
      return {
        id: `comfyui:${providerJobId}`,
        provider: "comfyui",
        providerJobId,
        status: "running",
        raw,
      };
    }

    const outputUrls = collectOutputUrls(entry);
    const statusText = entry.status?.status_str;
    const completed = entry.status?.completed === true || outputUrls.length > 0;
    const failed = statusText === "error" || statusText === "failed";

    return {
      id: `comfyui:${providerJobId}`,
      provider: "comfyui",
      providerJobId,
      status: failed ? "failed" : completed ? "completed" : "running",
      outputUrls: outputUrls.length ? outputUrls : undefined,
      error: failed ? JSON.stringify(entry.status) : undefined,
      raw: entry,
    };
  },
};
