/** Invented protocol/layout fixtures; these are NOT real browser rendering. */
import assert from "node:assert/strict";
import { PassThrough } from "node:stream";
import { checkLayout, PipeClient, validateBaselineRef } from "./check_public_demo_browser.mjs";

let checks = 0;
async function test(name, run) {
  await run();
  console.log(`ok ${++checks} - ${name}`);
}
const fixture = () => ({
  viewportWidth: 390, pageWidth: 390, duplicateIds: [], missingFragments: [],
  headingCount: 1, probabilitySum: "100.0%", navLinks: 4,
  focusTargets: ["overview", "workbench", "engineering-evidence", "reproduce-public"],
  hasPublicCommand: true, hasEvidenceBoundary: true,
});

await test("only exact nonzero Git SHA inputs are allowed", () => {
  assert.equal(validateBaselineRef("a".repeat(40)), "a".repeat(40));
  for (const bad of ["main", "--all", "0".repeat(40), "a".repeat(39), "A".repeat(40), "a".repeat(40) + ":path"]) {
    assert.throws(() => validateBaselineRef(bad));
  }
});
await test("matching narrow layout is accepted without a fake rendering claim", () => checkLayout(fixture(), 390));
await test("unintentional page overflow is rejected", () => assert.throws(() => checkLayout({ ...fixture(), pageWidth: 440 }, 390)));
await test("viewport mismatch and missing fragments are rejected", () => {
  assert.throws(() => checkLayout(fixture(), 320));
  assert.throws(() => checkLayout({ ...fixture(), missingFragments: ["absent"] }, 390));
});
await test("duplicate IDs and loss of probability conservation are rejected", () => {
  assert.throws(() => checkLayout({ ...fixture(), duplicateIds: ["repeated"] }, 390));
  assert.throws(() => checkLayout({ ...fixture(), probabilitySum: "99.0%" }, 390));
});
await test("review evidence and focus destinations are mandatory for current source", () => {
  assert.throws(() => checkLayout({ ...fixture(), hasEvidenceBoundary: false }, 390));
  assert.throws(() => checkLayout({ ...fixture(), focusTargets: [] }, 390));
  checkLayout({ ...fixture(), navLinks: 0, focusTargets: [], hasEvidenceBoundary: false }, 390, { current: false });
});
await test("Chrome pipe requests use a session and null-delimited JSON", async () => {
  const reader = new PassThrough(), writer = new PassThrough();
  const client = new PipeClient(reader, writer);
  const promise = client.send("Example.method", { value: 7 }, "session-one");
  const request = writer.read().toString();
  assert.equal(request.at(-1), "\0");
  assert.deepEqual(JSON.parse(request.slice(0, -1)), { id: 1, method: "Example.method", params: { value: 7 }, sessionId: "session-one" });
  reader.write(Buffer.from('{"id":1,"result":{"value":7}}\0'));
  assert.deepEqual(await promise, { value: 7 });
  client.close();
});
await test("split UTF-8 protocol messages and combined events are preserved", async () => {
  const reader = new PassThrough(), writer = new PassThrough();
  const client = new PipeClient(reader, writer);
  const promise = client.send("Example");
  const message = Buffer.from('{"method":"Event","sessionId":"s"}\0{"id":1,"result":{"label":"é"}}\0');
  const split = message.indexOf(Buffer.from("é")) + 1;
  reader.write(message.subarray(0, split));
  reader.write(message.subarray(split));
  assert.deepEqual(await promise, { label: "é" });
  assert.equal(client.events.length, 1);
  assert.equal(client.events[0].sessionId, "s");
  client.close();
});
await test("Chrome protocol errors retain method context", async () => {
  const reader = new PassThrough(), writer = new PassThrough();
  const client = new PipeClient(reader, writer);
  const promise = client.send("Missing.method");
  reader.write(Buffer.from('{"id":1,"error":{"message":"unknown method"}}\0'));
  await assert.rejects(promise, /Missing.method: unknown method/);
  client.close();
});
await test("bad protocol JSON closes pending work without fabricated pass", async () => {
  const reader = new PassThrough(), writer = new PassThrough();
  const client = new PipeClient(reader, writer);
  const promise = client.send("Example");
  reader.write(Buffer.from("not-json\0"));
  await assert.rejects(promise, /invalid JSON/);
  await assert.rejects(client.send("Later"), /invalid JSON/);
});
await test("a stalled Chrome request is a bounded failure", async () => {
  const reader = new PassThrough(), writer = new PassThrough();
  const client = new PipeClient(reader, writer, { timeout: 10 });
  await assert.rejects(client.send("Stalled"), /timeout: Stalled/);
  assert.equal(client.pending.size, 0);
  client.close();
});
console.log(`PASS ${checks} browser-checker fixture tests; real rendering is a separate required check.`);
