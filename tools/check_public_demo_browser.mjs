/**
 * Real-renderer review using an already-installed Chrome/Chromium and Node built-ins.
 * No browser download, npm dependency, web server, cloud credential or provider call.
 */
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT = path.join(ROOT, "outputs/browser-review");
const PUBLIC_FILES = ["index.html", "styles.css", "data.js", "engine.js", "app.js"];
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
  { name: "narrow-mobile", width: 320, height: 780 },
];

function filePin(filename) {
  const body = fs.readFileSync(filename);
  return { bytes: body.length, sha256: createHash("sha256").update(body).digest("hex") };
}

export class PipeClient {
  constructor(reader, writer, { timeout = 15000 } = {}) {
    this.writer = writer;
    this.timeout = timeout;
    this.buffer = Buffer.alloc(0);
    this.counter = 0;
    this.pending = new Map();
    this.events = [];
    this.failure = null;
    reader.on("data", (chunk) => this.receive(chunk));
    reader.on("error", (error) => this.close(error));
    writer.on("error", (error) => this.close(error));
  }

  receive(chunk) {
    this.buffer = Buffer.concat([this.buffer, chunk]);
    if (this.buffer.length > 32 * 1024 * 1024) {
      this.close(new Error("Chrome protocol message exceeded 32 MiB."));
      return;
    }
    let end;
    while ((end = this.buffer.indexOf(0)) >= 0) {
      const bytes = this.buffer.subarray(0, end);
      this.buffer = this.buffer.subarray(end + 1);
      if (bytes.length === 0) continue;
      let message;
      try {
        message = JSON.parse(bytes.toString("utf8"));
      } catch {
        this.close(new Error("Chrome returned an invalid JSON protocol message."));
        return;
      }
      if (!message.id) {
        this.events.push(message);
        continue;
      }
      const request = this.pending.get(message.id);
      if (!request) continue;
      clearTimeout(request.timer);
      this.pending.delete(message.id);
      if (message.error) request.reject(new Error(`${request.method}: ${message.error.message}`));
      else request.resolve(message.result);
    }
  }

  send(method, params = {}, sessionId) {
    if (this.failure) return Promise.reject(this.failure);
    const id = ++this.counter;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Chrome protocol timeout: ${method}`));
      }, this.timeout);
      this.pending.set(id, { resolve, reject, timer, method });
      this.writer.write(`${JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) })}\0`);
    });
  }

  close(error = new Error("Chrome protocol pipe closed.")) {
    this.failure = error;
    for (const request of this.pending.values()) {
      clearTimeout(request.timer);
      request.reject(error);
    }
    this.pending.clear();
  }
}

export function validateBaselineRef(value) {
  if (!/^[a-f0-9]{40}$/.test(value) || /^0+$/.test(value)) {
    throw new Error("--baseline-ref requires a nonzero, exact 40-character Git commit SHA.");
  }
  return value;
}

export function checkLayout(layout, width, { current = true } = {}) {
  assert.equal(layout.viewportWidth, width, "browser viewport must match the requested width");
  assert.ok(layout.pageWidth <= width + 1, `unexpected page overflow: ${layout.pageWidth}px at ${width}px`);
  assert.equal(layout.duplicateIds.length, 0, "duplicate element IDs");
  assert.equal(layout.missingFragments.length, 0, "in-page links must resolve");
  assert.equal(layout.headingCount, 1, "one primary page heading");
  assert.equal(layout.probabilitySum, "100.0%", "rendered engine probability conservation");
  if (current) {
    assert.equal(layout.navLinks, 4, "four reviewer navigation links");
    assert.equal(layout.focusTargets.length, 4, "all reviewer destinations must receive focus");
    assert.ok(layout.hasPublicCommand, "public reproduction command is visible in the DOM");
    assert.ok(layout.hasEvidenceBoundary, "historical result must be distinct from the synthetic scenario");
  }
}

function installedBrowser() {
  const configured = process.env.CHROME_BIN;
  const names = configured ? [configured] : ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"];
  for (const name of names) {
    const candidates = path.isAbsolute(name) || name.includes(path.sep)
      ? [path.resolve(name)]
      : (process.env.PATH || "").split(path.delimiter).filter(Boolean).map((dir) => path.join(dir, name));
    for (const candidate of candidates) {
      try {
        fs.accessSync(candidate, fs.constants.X_OK);
        if (fs.statSync(candidate).isFile()) return candidate;
      } catch { /* Only installed, executable files are eligible. */ }
    }
  }
  throw new Error("No installed Chrome/Chromium found. Set CHROME_BIN to an existing executable; this checker never downloads one. Rendering is UNVERIFIED.");
}

function baselineTree(ref, temporary) {
  validateBaselineRef(ref);
  const kind = spawnSync("git", ["cat-file", "-t", ref], { cwd: ROOT, encoding: "utf8" });
  assert.equal(kind.status, 0, "baseline commit must exist in the local clone");
  assert.equal(kind.stdout.trim(), "commit", "baseline object must be a commit");
  const directory = path.join(temporary, "baseline/public-demo");
  fs.mkdirSync(directory, { recursive: true });
  for (const name of PUBLIC_FILES) {
    const file = spawnSync("git", ["show", `${ref}:public-demo/${name}`], { cwd: ROOT, maxBuffer: 8 * 1024 * 1024 });
    assert.equal(file.status, 0, `baseline must contain public-demo/${name}`);
    fs.writeFileSync(path.join(directory, name), file.stdout);
  }
  return path.join(directory, "index.html");
}

async function evaluate(client, session, expression) {
  const result = await client.send("Runtime.evaluate", {
    expression, returnByValue: true, awaitPromise: true,
  }, session);
  if (result.exceptionDetails) throw new Error(`Page evaluation failed: ${JSON.stringify(result.exceptionDetails)}`);
  return result.result.value;
}

async function render(client, filename, viewport, label, report) {
  const { targetId } = await client.send("Target.createTarget", { url: "about:blank" });
  const { sessionId: session } = await client.send("Target.attachToTarget", { targetId, flatten: true });
  const result = {
    source: label, viewport, status: "STARTED", screenshots: [],
    sourceFiles: Object.fromEntries(PUBLIC_FILES.map((name) => [name, filePin(path.join(path.dirname(filename), name))])),
  };
  report.renders.push(result);
  try {
    await client.send("Page.enable", {}, session);
    await client.send("Runtime.enable", {}, session);
    await client.send("Network.enable", {}, session);
    await client.send("Network.setBlockedURLs", { urls: ["http://*", "https://*"] }, session);
    await client.send("Emulation.setDeviceMetricsOverride", {
      width: viewport.width, height: viewport.height, deviceScaleFactor: 1, mobile: false,
    }, session);
    await client.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] }, session);
    const navigation = await client.send("Page.navigate", { url: pathToFileURL(filename).href }, session);
    assert.ok(!navigation.errorText, navigation.errorText);
    const started = Date.now();
    let ready = false;
    while (Date.now() - started < 10000) {
      ready = await evaluate(client, session, 'document.readyState === "complete" && document.getElementById("total-probability")?.textContent === "100.0%"');
      if (ready) break;
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    assert.ok(ready, "real browser did not render a complete probability-conserving forecast");
    await evaluate(client, session, "document.fonts.ready.then(() => true)");
    result.layout = await evaluate(client, session, `(() => {
      const ids = [...document.querySelectorAll('[id]')].map(node => node.id);
      return {
        viewportWidth: window.innerWidth,
        pageWidth: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
        duplicateIds: ids.filter((id, index) => ids.indexOf(id) !== index),
        missingFragments: [...document.querySelectorAll('a[href^="#"]')].map(node => node.getAttribute('href').slice(1)).filter(id => id && !document.getElementById(id)),
        headingCount: document.querySelectorAll('h1').length,
        probabilitySum: document.getElementById('total-probability').textContent,
        navLinks: document.querySelectorAll('.review-nav a').length,
        focusTargets: ['overview','workbench','engineering-evidence','reproduce-public'].filter(id => document.getElementById(id)?.getAttribute('tabindex') === '-1'),
        hasPublicCommand: document.body.textContent.includes('python tools/review_project.py'),
        hasEvidenceBoundary: document.body.textContent.includes('PRIVATE FORECAST · PUBLIC AGGREGATE') && document.body.textContent.includes('PUBLIC SCENARIO LAB · SYNTHETIC INPUTS'),
        bracketViewport: { client: document.getElementById('bracket-viewport').clientWidth, scroll: document.getElementById('bracket-viewport').scrollWidth },
      };
    })()`);
    // Save honest screenshots even if a layout assertion subsequently fails.
    const metrics = await client.send("Page.getLayoutMetrics", {}, session);
    const height = Math.ceil(metrics.cssContentSize?.height ?? metrics.contentSize.height);
    assert.ok(height <= 20000, "unexpected content height; refusing a truncated full-page claim");
    for (const [kind, extra] of [
      ["viewport", {}],
      ["full-page", { captureBeyondViewport: true, clip: { x: 0, y: 0, width: viewport.width, height, scale: 1 } }],
    ]) {
      const screenshot = await client.send("Page.captureScreenshot", { format: "png", ...extra }, session);
      const name = `${label}-${viewport.name}-${kind}.png`;
      fs.writeFileSync(path.join(OUTPUT, name), Buffer.from(screenshot.data, "base64"));
      result.screenshots.push({ file: name, ...filePin(path.join(OUTPUT, name)) });
    }
    if (label === "baseline") {
      // Before-images document the original source; old UX is not made to pass new requirements.
      try { checkLayout(result.layout, viewport.width, { current: false }); }
      catch (error) { result.baselineFinding = error.message; }
    } else checkLayout(result.layout, viewport.width);

    result.interactions = await evaluate(client, session, `(() => {
      const byId = id => document.getElementById(id);
      byId('preset-even').click();
      const even = byId('duke-title-probability').textContent;
      byId('focus-michigan').click();
      const focus = byId('team').value;
      byId('rating').value = '100';
      byId('rating').dispatchEvent(new Event('input', { bubbles: true }));
      const adjusted = byId('rating-value').textContent;
      byId('reset').click();
      byId('focus-duke').click();
      return { even, focus, adjusted, selected: byId('team').value, probabilitySum: byId('total-probability').textContent, errorHidden: byId('error').hidden };
    })()`);
    assert.equal(result.interactions.even, "12.5%");
    assert.equal(result.interactions.focus, "michigan");
    assert.equal(result.interactions.adjusted, "+100");
    assert.equal(result.interactions.selected, "duke");
    assert.equal(result.interactions.probabilitySum, "100.0%");
    assert.equal(result.interactions.errorHidden, true);

    // Native keyboard events, not only a fake DOM or programmatic focus assertion.
    await evaluate(client, session, 'document.activeElement?.blur(); window.scrollTo(0, 0); document.body.tabIndex = -1; document.body.focus();');
    await client.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 }, session);
    await client.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 }, session);
    result.keyboard = await evaluate(client, session, `({ firstTarget: document.activeElement?.getAttribute('href'), firstText: document.activeElement?.textContent.trim() })`);
    assert.equal(result.keyboard.firstTarget, "#workbench", "first keyboard destination is the skip link");
    await client.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 }, session);
    await client.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 }, session);
    result.keyboard.afterSkip = await evaluate(client, session, "document.activeElement?.id");
    if (label === "current") assert.equal(result.keyboard.afterSkip, "workbench", "skip link transfers focus to main content");

    if (label === "current") {
      result.navigation = await evaluate(client, session, `(() => {
        const link = document.querySelector('.review-nav a[href="#reproduce-public"]');
        link.click();
        return { hash: location.hash, probabilitySum: document.getElementById('total-probability').textContent };
      })()`);
      assert.equal(result.navigation.hash, "#reproduce-public");
      assert.equal(result.navigation.probabilitySum, "100.0%", "ordinary navigation does not mutate a scenario");
    }
    const events = client.events.filter((event) => event.sessionId === session);
    result.pageHttpAttempts = events.filter((event) => event.method === "Network.requestWillBeSent" && /^https?:/.test(event.params.request.url)).map((event) => event.params.request.url);
    result.pageErrors = events.filter((event) => event.method === "Runtime.exceptionThrown").map((event) => event.params.exceptionDetails.text);
    assert.deepEqual(result.pageHttpAttempts, [], "the page must make no HTTP(S) requests");
    assert.deepEqual(result.pageErrors, [], "no uncaught browser exceptions");
    result.status = "PASS";
  } catch (error) {
    result.status = "FAIL";
    result.error = error.message;
    throw error;
  } finally {
    await client.send("Target.closeTarget", { targetId }).catch(() => {});
  }
}

export async function main(args = process.argv.slice(2)) {
  if (args.includes("--help")) {
    console.log("node tools/check_public_demo_browser.mjs [--baseline-ref EXACT_COMMIT_SHA]\nUses existing Chrome/Chromium only; writes screenshots and a real-renderer report under outputs/browser-review/.");
    return 0;
  }
  const report = {
    schema: "march.public_browser_review.v1", status: "STARTED", rendererVerified: false,
    startedAtUtc: new Date().toISOString(),
    scope: "Public synthetic UI only. Not private model validation, a SageMaker owner run or an accessibility conformance certification.",
    runtimeDownloads: 0, externalAppRequestsAllowed: false, baselineRef: null, renders: [],
  };
  fs.mkdirSync(OUTPUT, { recursive: true });
  let temporary, browser, client;
  const start = performance.now();
  try {
    let baselineRef;
    if (args.length !== 0) {
      assert.equal(args.length, 2, "only --baseline-ref EXACT_COMMIT_SHA is accepted");
      assert.equal(args[0], "--baseline-ref", "unknown argument");
      baselineRef = validateBaselineRef(args[1]);
      report.baselineRef = baselineRef;
    }
    const executable = installedBrowser();
    temporary = fs.mkdtempSync(path.join(os.tmpdir(), "march-public-browser-"));
    const baseline = baselineRef ? baselineTree(baselineRef, temporary) : null;
    browser = spawn(executable, [
      "--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--disable-background-networking",
      "--disable-component-update", "--disable-sync", "--disable-breakpad", "--no-first-run",
      "--no-default-browser-check", "--no-proxy-server", "--host-resolver-rules=MAP * ~NOTFOUND",
      "--disable-features=MediaRouter,OptimizationHints,Translate,AutofillServerCommunication",
      "--remote-debugging-pipe", `--user-data-dir=${path.join(temporary, "chrome-profile")}`, "about:blank",
    ], { stdio: ["ignore", "ignore", "pipe", "pipe", "pipe"] });
    client = new PipeClient(browser.stdio[4], browser.stdio[3]);
    let stderr = "";
    browser.stderr.on("data", (chunk) => { stderr = (stderr + chunk.toString()).slice(-12000); });
    browser.on("error", (error) => client.close(error));
    browser.on("exit", (code) => client.close(new Error(`Chrome exited (${code}). ${stderr.slice(-2000)}`)));
    report.browser = await client.send("Browser.getVersion");
    for (const viewport of VIEWPORTS) {
      // A failed viewport must not hide useful screenshots from the remaining sizes.
      await render(client, path.join(ROOT, "public-demo/index.html"), viewport, "current", report).catch(() => {});
      if (baseline) await render(client, baseline, viewport, "baseline", report).catch(() => {});
    }
    const current = report.renders.filter((item) => item.source === "current");
    assert.equal(current.length, VIEWPORTS.length, "every current viewport must be reached");
    assert.ok(current.every((item) => item.status === "PASS"), "one or more current browser viewports failed; inspect the complete report and screenshots");
    // Baseline defects remain evidence about the prior source, not a veto of a fixed version.
    report.baselineFindings = report.renders.filter((item) => item.source === "baseline" && (item.error || item.baselineFinding)).map((item) => ({ viewport: item.viewport.name, finding: item.error || item.baselineFinding }));
    report.status = "PASS";
    report.rendererVerified = true;
    return 0;
  } catch (error) {
    report.status = report.renders.length ? "FAIL" : "BLOCKED";
    report.error = error.message;
    console.error(error.message);
    return 1;
  } finally {
    if (client) await client.send("Browser.close").catch(() => {});
    // Only the child launched above is stopped; never an existing user browser.
    if (browser && browser.exitCode === null) browser.kill("SIGTERM");
    if (temporary) {
      try { fs.rmSync(temporary, { recursive: true, force: true, maxRetries: 3 }); }
      catch (error) { report.temporaryCleanupWarning = error.message; }
    }
    report.elapsedSeconds = Number(((performance.now() - start) / 1000).toFixed(3));
    fs.writeFileSync(path.join(OUTPUT, "browser_review.json"), `${JSON.stringify(report, null, 2)}\n`);
    console.log(`BROWSER_REVIEW_STATUS=${report.status}`);
    console.log("BROWSER_REVIEW_REPORT=outputs/browser-review/browser_review.json");
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main();
}
