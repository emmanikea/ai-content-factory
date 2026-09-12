#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fal } from '@fal-ai/client';

function parseArgs(argv) {
  const args = { live: false, job: null, outdir: null };
  for (let i = 2; i < argv.length; i++) {
    const value = argv[i];
    if (value === '--live') args.live = true;
    else if (value === '--job') args.job = argv[++i];
    else if (value === '--outdir') args.outdir = argv[++i];
    else throw new Error(`Unknown argument: ${value}`);
  }
  if (!args.job) throw new Error('Usage: node render.mjs --job job.json [--outdir dir] [--live]');
  return args;
}

function findMediaUrl(data) {
  const candidates = [
    data?.video?.url,
    data?.output?.video?.url,
    data?.videos?.[0]?.url,
    data?.image?.url,
    data?.images?.[0]?.url,
  ];
  return candidates.find(Boolean) ?? null;
}

async function download(url, destination) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Download failed: ${response.status} ${response.statusText}`);
  const bytes = Buffer.from(await response.arrayBuffer());
  await fs.writeFile(destination, bytes);
}

async function main() {
  const args = parseArgs(process.argv);
  const raw = await fs.readFile(args.job, 'utf8');
  const job = JSON.parse(raw);

  if (job.provider !== 'fal') throw new Error(`Unsupported provider: ${job.provider}`);
  if (!job.model_id || !job.input) throw new Error('job.model_id and job.input are required');

  const preview = {
    mode: args.live ? 'live' : 'dry-run',
    provider: 'fal',
    model_id: job.model_id,
    estimated_cost_usd: job.estimated_cost_usd ?? null,
    input: job.input,
  };

  if (!args.live) {
    console.log(JSON.stringify(preview, null, 2));
    return;
  }

  if (!process.env.FAL_KEY) {
    throw new Error('FAL_KEY is required for --live. Dry-run mode never needs credentials.');
  }
  if (job.approved_for_spend !== true) {
    throw new Error('Live render blocked: job.approved_for_spend must be true.');
  }

  const outdir = path.resolve(args.outdir ?? path.join(process.cwd(), 'fal-output'));
  await fs.mkdir(outdir, { recursive: true });

  const startedAt = new Date().toISOString();
  const result = await fal.subscribe(job.model_id, {
    input: job.input,
    logs: true,
    onQueueUpdate(update) {
      if (update.status === 'IN_PROGRESS' && Array.isArray(update.logs)) {
        for (const entry of update.logs) {
          if (entry?.message) process.stderr.write(`[fal] ${entry.message}\n`);
        }
      }
    },
  });

  const mediaUrl = findMediaUrl(result.data);
  const provenance = {
    provider: 'fal',
    model_id: job.model_id,
    request_id: result.requestId ?? null,
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    estimated_cost_usd: job.estimated_cost_usd ?? null,
    approved_for_spend: true,
    input: job.input,
    result: result.data,
    media_url: mediaUrl,
  };

  await fs.writeFile(
    path.join(outdir, 'provenance.json'),
    `${JSON.stringify(provenance, null, 2)}\n`,
    'utf8',
  );

  if (mediaUrl) {
    const pathname = new URL(mediaUrl).pathname;
    const ext = path.extname(pathname) || '.mp4';
    await download(mediaUrl, path.join(outdir, `asset${ext}`));
  }

  console.log(JSON.stringify({
    request_id: result.requestId ?? null,
    media_url: mediaUrl,
    outdir,
  }, null, 2));
}

main().catch(error => {
  console.error(error?.stack || String(error));
  process.exit(1);
});
