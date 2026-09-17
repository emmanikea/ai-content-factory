#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { chromium } from 'playwright';

function parseArgs(argv) {
  const args = { spec: null, outdir: null, headed: false };
  for (let i = 2; i < argv.length; i++) {
    const value = argv[i];
    if (value === '--spec') args.spec = argv[++i];
    else if (value === '--outdir') args.outdir = argv[++i];
    else if (value === '--headed') args.headed = true;
    else throw new Error(`Unknown argument: ${value}`);
  }
  if (!args.spec) throw new Error('Usage: node capture.mjs --spec capture.json [--outdir dir] [--headed]');
  return args;
}

async function perform(page, action) {
  switch (action.type) {
    case 'goto':
      await page.goto(action.url, { waitUntil: action.wait_until ?? 'networkidle' });
      break;
    case 'click':
      await page.locator(action.selector).click({ timeout: action.timeout_ms ?? 10000 });
      break;
    case 'tap':
      await page.locator(action.selector).tap({ timeout: action.timeout_ms ?? 10000 });
      break;
    case 'fill':
      await page.locator(action.selector).fill(action.value ?? '');
      break;
    case 'press':
      await page.locator(action.selector).press(action.key);
      break;
    case 'wait':
      await page.waitForTimeout(action.ms ?? 500);
      break;
    case 'wait_for':
      await page.locator(action.selector).waitFor({ state: action.state ?? 'visible', timeout: action.timeout_ms ?? 10000 });
      break;
    case 'scroll':
      await page.mouse.wheel(action.x ?? 0, action.y ?? 500);
      break;
    case 'screenshot':
      await page.screenshot({ path: action.path, fullPage: Boolean(action.full_page) });
      break;
    default:
      throw new Error(`Unsupported capture action: ${action.type}`);
  }
}

async function main() {
  const args = parseArgs(process.argv);
  const spec = JSON.parse(await fs.readFile(args.spec, 'utf8'));
  const outdir = path.resolve(args.outdir ?? path.join(process.cwd(), 'capture-output'));
  await fs.mkdir(outdir, { recursive: true });

  const viewport = spec.viewport ?? { width: 390, height: 844 };
  const browser = await chromium.launch({ headless: !args.headed });
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: spec.device_scale_factor ?? 1,
    isMobile: spec.is_mobile ?? true,
    hasTouch: spec.has_touch ?? true,
    recordVideo: {
      dir: outdir,
      size: spec.video_size ?? { width: 720, height: 1280 },
    },
  });

  const page = await context.newPage();
  const video = page.video();
  const startedAt = new Date().toISOString();

  try {
    if (spec.start_url) {
      await page.goto(spec.start_url, { waitUntil: spec.wait_until ?? 'networkidle' });
    }
    for (const action of spec.actions ?? []) {
      await perform(page, action);
    }
    if (spec.hold_final_ms) {
      await page.waitForTimeout(spec.hold_final_ms);
    }
  } finally {
    await page.close();
    await context.close();
    await browser.close();
  }

  const recordedPath = video ? await video.path() : null;
  const finalPath = path.join(outdir, spec.output_name ?? 'capture.webm');
  if (recordedPath && recordedPath !== finalPath) {
    await fs.rename(recordedPath, finalPath);
  }

  const provenance = {
    type: 'app_capture',
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    start_url: spec.start_url ?? null,
    viewport,
    action_count: (spec.actions ?? []).length,
    output: finalPath,
    deterministic: true,
  };
  await fs.writeFile(path.join(outdir, 'capture-provenance.json'), `${JSON.stringify(provenance, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(provenance, null, 2));
}

main().catch(error => {
  console.error(error?.stack || String(error));
  process.exit(1);
});
