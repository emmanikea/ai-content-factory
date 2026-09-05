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

function authHeaders(includeJson = true): HeadersInit {
  const token = process.env.COMFYUI_API_TOKEN;
  return {
    ...(includeJson ? { "Content-Type": "application/json" } : {}),
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

type BindingMap = Record<string, { node: string; input: string }>;

function parseBindings(raw: string | undefined): BindingMap | undefined {
  if (!raw) return undefined;
  const parsed = JSON.parse(raw) as unknown;
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("COMFYUI_BINDINGS_JSON must be a JSON object");
  }
  return parsed as BindingMap;
}

function workflowFromRequest(input: GenerationRequest): Record<string, unknown> {
  const unsafeOverrides = process.env.COMFYUI_ALLOW_CLIENT_WORKFLOW_OVERRIDES === "true";
  const direct = input.providerOptions?.workflow;
  const directBindings = input.providerOptions?.bindings;

  if (!unsafeOverrides && (direct !== undefined || directBindings !== undefined)) {
    throw new Error(
      "Client-supplied ComfyUI workflow/binding overrides are disabled. Configure the tested workflow server-side.",
    );
  }

  let workflow: Record<string, any>;
  if (unsafeOverrides && direct && typeof direct === "object") {
    workflow = JSON.parse(JSON.stringify(direct)) as Record<string, any>;
  } else {
    const encoded = process.env.COMFYUI_WORKFLOW_JSON;
    if (!encoded) {
      throw new Error(
        "COMFYUI_WORKFLOW_JSON is not configured. Export a tested API-format workflow and configure it server-side.",
      );
    }
    workflow = JSON.parse(encoded) as Record<string, any>;
  }

  const bindings = unsafeOverrides && directBindings && typeof directBindings === "object"
    ? directBindings as BindingMap
    : parseBindings(process.env.COMFYUI_BINDINGS_JSON);

  const values: Record<string, unknown> = {
    prompt: input.prompt,
    duration: input.duration,
    resolution: input.resolution,
    aspectRatio: input.aspectRatio,
    generateAudio: input.generateAudio,
  };

  input.inputReferences?.forEach((reference, index) => {
    values[`reference${index}`] = reference.url;
  });
  input.frameImages?.forEach((frame) => {
    values[`frame_${frame.frameType}`] = frame.url;
  });

  if (bindings) {
    for (const [key, binding] of Object.entries(bindings)) {
      const value = values[key];
      if (value === undefined) continue;
      const node = workflow[binding.node] as Record<string, any> | undefined;
      if (!node?.inputs || typeof binding.input !== "string") {
        throw new Error(`Invalid ComfyUI binding for ${key}`);
      }
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

export async function fetchComfyOutput(
  providerJobId: string,
  index = 0,
  range?: string,
): Promise<Response> {
  const job = await comfyUiProvider.get(providerJobId);
  const outputUrl = job.outputUrls?.[index];
  if (job.status !== "completed" || !outputUrl) {
    throw new Error(`ComfyUI output ${index} is not available for ${providerJobId}`);
  }

  const expectedPrefix = `${baseUrl()}/view?`;
  if (!outputUrl.startsWith(expectedPrefix)) {
    throw new Error("Refusing to proxy a ComfyUI output outside the configured server");
  }

  const response = await fetch(outputUrl, {
    headers: {
      ...authHeaders(false),
      ...(range ? { Range: range } : {}),
    },
    cache: "no-store",
  });
  if (!response.ok && response.status !== 206) {
    const body = await response.text();
    throw new Error(`ComfyUI output ${response.status}: ${body.slice(0, 800)}`);
  }
  return response;
}
