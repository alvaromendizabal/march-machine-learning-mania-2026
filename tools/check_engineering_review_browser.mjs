/** Inspect the generated employer review in an installed real Chrome, offline. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { PipeClient, installedBrowser } from "./check_public_demo_browser.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "outputs/browser-review/engineering");
const VIEWS = [[1440, 1100], [768, 1024], [390, 844], [320, 780]];
const pin = raw => ({ bytes: raw.length, sha256: createHash("sha256").update(raw).digest("hex") });

export function validateProofLayout(layout, width) {
  assert.equal(layout.viewportWidth, width, "requested real viewport");
  assert.ok(layout.pageWidth <= width + 1, "no horizontal page overflow");
  assert.deepEqual(layout.duplicateIds, [], "unique section identities");
  assert.deepEqual(layout.missingTargets, [], "all review navigation targets exist");
  assert.equal(layout.primaryHeadings, 1, "one primary heading");
  assert.equal(layout.cards.length, 3, "three explicit verification layers");
  for (const card of layout.cards) {
    assert.ok(card.left >= 0 && card.right <= width + 1, "proof cards remain in viewport");
    assert.ok(card.right > card.left && card.bottom > card.top, "visible nonempty card");
  }
  if (width <= 700) {
    for (let i = 1; i < layout.cards.length; i += 1)
      assert.ok(layout.cards[i].top >= layout.cards[i - 1].bottom, "mobile cards stack in reading order");
  } else {
    assert.ok(layout.cards.every(card => Math.abs(card.top - layout.cards[0].top) <= 1), "wide cards align");
  }
  assert.equal(layout.scopeDisclosed, true, "fixture tests do not certify an unseen CI run");
  assert.equal(layout.trustDisclosed, true, "internal consistency is not authorship");
}

export function validateProofNavigation(value) {
  assert.equal(value.hash, "#execution-proof");
  assert.equal(value.activeElement, "execution-proof", "native anchor transfers focus");
  assert.ok(value.top >= -1 && value.top < value.height, "named destination is visible");
  assert.equal(value.detailsOpen, true, "native disclosure is operable");
  assert.equal(value.commandVisible, true, "verification command is visible after disclosure");
}

async function evaluate(client, session, expression) {
  const result = await client.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }, session);
  assert.equal(result.exceptionDetails, undefined, "browser expression executed successfully");
  return result.result.value;
}

async function capture(client, session, row, label) {
  const shot = await client.send("Page.captureScreenshot", { format: "png" }, session);
  const body = Buffer.from(shot.data, "base64");
  const filename = `review-${row.width}-${label}.png`;
  fs.writeFileSync(path.join(OUT, filename), body);
  row.screenshots.push({ file: filename, ...pin(body) });
}

async function render(client, width, height, report) {
  const row = { width, height, status: "STARTED", screenshots: [] };
  report.renders.push(row);
  const { targetId } = await client.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await client.send("Target.attachToTarget", { targetId, flatten: true });
  try {
    for (const method of ["Page.enable", "Runtime.enable", "Network.enable"])
      await client.send(method, {}, sessionId);
    await client.send("Network.setBlockedURLs", { urls: ["http://*", "https://*"] }, sessionId);
    await client.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width <= 700 }, sessionId);
    await client.send("Page.navigate", { url: pathToFileURL(path.join(ROOT, "outputs/review/index.html")).href }, sessionId);
    await evaluate(client, sessionId, `(async () => {
      if (document.readyState !== 'complete') await new Promise(resolve => window.addEventListener('load', resolve, {once:true}));
      await document.fonts.ready;
      scrollTo({top:0,left:0,behavior:'instant'});
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      return true;
    })()`);
    row.origin = await evaluate(client, sessionId, "({x:scrollX,y:scrollY})");
    assert.deepEqual(row.origin, { x: 0, y: 0 }, "capture begins at the real page origin");
    row.layout = await evaluate(client, sessionId, `(() => {
      const ids = [...document.querySelectorAll('[id]')].map(n => n.id);
      const bounds = n => {const {left,right,top,bottom} = n.getBoundingClientRect();return {left,right,top,bottom};};
      return {
        viewportWidth:innerWidth,pageWidth:Math.max(document.documentElement.scrollWidth,document.body.scrollWidth),
        duplicateIds:ids.filter((id,i)=>ids.indexOf(id)!==i),
        missingTargets:[...document.querySelectorAll('.review-nav a[href^="#"]')].map(n=>n.hash.slice(1)).filter(id=>!document.getElementById(id)),
        primaryHeadings:document.querySelectorAll('h1').length,
        outsideRequestedWidth:[...document.querySelectorAll('body *')].filter(n=>{
          const b=n.getBoundingClientRect();
          if(b.right<=${width}+1 || b.width===0) return false;
          for(let p=n.parentElement;p;p=p.parentElement) if(['auto','scroll','hidden','clip'].includes(getComputedStyle(p).overflowX)) return false;
          return true;
        }).slice(0,20).map(n=>({tag:n.tagName,id:n.id,className:String(n.className),...bounds(n)})),
        cards:[...document.querySelectorAll('.proof-grid li')].map(bounds),
        scopeDisclosed:document.querySelector('#execution-proof').textContent.includes('not silently download or certify a real CI run'),
        trustDisclosed:document.querySelector('#execution-proof').textContent.includes('internal consistency is not authorship')
      };
    })()`);
    await capture(client, sessionId, row, "origin");
    validateProofLayout(row.layout, width);
    await evaluate(client, sessionId, `(() => {
      document.documentElement.style.scrollBehavior='auto';
      const link = document.querySelector('a[href="#execution-proof"]'); link.focus();link.click();
      document.querySelector('#execution-proof summary').click();
      return true;
    })()`);
    await evaluate(client, sessionId, "new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve(true))))");
    row.navigation = await evaluate(client, sessionId, `(() => {
      const section=document.getElementById('execution-proof'), command=section.querySelector('code');
      return {hash:location.hash,activeElement:document.activeElement.id,top:section.getBoundingClientRect().top,height:innerHeight,
        detailsOpen:section.querySelector('details').open,commandVisible:command.getClientRects().length>0};
    })()`);
    validateProofNavigation(row.navigation);
    await capture(client, sessionId, row, "proof");
    row.httpAttempts = client.events.filter(e=>e.sessionId===sessionId && e.method==="Network.requestWillBeSent" && /^https?:/.test(e.params.request.url)).length;
    row.uncaughtExceptions = client.events.filter(e=>e.sessionId===sessionId && e.method==="Runtime.exceptionThrown").length;
    assert.equal(row.httpAttempts, 0, "report makes no HTTP requests");
    assert.equal(row.uncaughtExceptions, 0, "no browser exceptions");
    row.status = "PASS";
  } catch (error) {
    row.status = "FAIL"; row.error = error.message;
  } finally {
    await client.send("Target.closeTarget", { targetId }).catch(()=>{});
  }
}

export async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const report = { schema: "march.engineering_review_browser.v1", status: "STARTED", renders: [],
    scope: "Actual installed Chrome, four emulated viewports; not full accessibility or cross-browser certification.",
    source: {}, startedAt: new Date().toISOString() };
  let temporary, browser, client;
  let stderr = "";
  const start = performance.now();
  try {
    for (const file of ["outputs/review/index.html", "outputs/review/review.json", "tools/review_template.html", "tools/review_project.py", "tools/check_engineering_review_browser.mjs"])
      report.source[file] = pin(fs.readFileSync(path.join(ROOT, file)));
    temporary = fs.mkdtempSync(path.join(os.tmpdir(), "march-review-browser-"));
    browser = spawn(installedBrowser(), ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--disable-background-networking",
      "--disable-component-update", "--disable-sync", "--disable-breakpad", "--no-first-run", "--no-default-browser-check",
      "--no-proxy-server", "--host-resolver-rules=MAP * ~NOTFOUND", "--remote-debugging-pipe",
      `--user-data-dir=${path.join(temporary,"profile")}`, "about:blank"], { stdio:["ignore","ignore","pipe","pipe","pipe"] });
    client = new PipeClient(browser.stdio[4],browser.stdio[3]);
    browser.stderr.on("data", chunk=>{stderr=(stderr+chunk.toString()).slice(-2000);});
    browser.on("error", e=>client.close(e));
    browser.on("exit", code=>client.close(new Error(`Chrome exited ${code}: ${stderr}`)));
    report.browser = await client.send("Browser.getVersion");
    for (const [width,height] of VIEWS) await render(client,width,height,report);
    assert.equal(report.renders.length,4);
    assert.ok(report.renders.every(r=>r.status==="PASS"),"one or more review viewports failed");
    report.status="PASS";
    return 0;
  } catch(error) {
    report.status=report.renders.length?"FAIL":"BLOCKED";report.error=error.message;
    return 1;
  } finally {
    if(report.status!=="PASS") report.browserStderrTail=stderr;
    if(client) await client.send("Browser.close").catch(()=>{});
    if(browser && browser.exitCode===null) browser.kill("SIGTERM");
    if(temporary) {try {fs.rmSync(temporary,{recursive:true,force:true,maxRetries:3});} catch(error) {report.cleanupWarning=error.message;}}
    report.elapsedSeconds=Number(((performance.now()-start)/1000).toFixed(3));
    fs.writeFileSync(path.join(OUT,"engineering_review_browser.json"),JSON.stringify(report,null,2)+"\n");
    console.log(`ENGINEERING_REVIEW_BROWSER_STATUS=${report.status}`);
  }
}

if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) process.exitCode=await main();
